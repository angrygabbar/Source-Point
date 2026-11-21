"""Send Android invoice alerts through Firebase Cloud Messaging HTTP v1."""

import hashlib
import json
import logging
import os
from pathlib import Path

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account
from sqlalchemy import func

from extensions import db
from models.auth import User
from models.commerce import Invoice
from models.mobile_support import MobilePushDevice

logger = logging.getLogger(__name__)
FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


def installation_id_digest(installation_id):
    return hashlib.sha256(installation_id.encode("utf-8")).hexdigest()


def _service_account_info():
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        return json.loads(raw)
    path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_FILE", "").strip()
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return None


def _access_token():
    info = _service_account_info()
    if not info:
        return None, None
    credentials = service_account.Credentials.from_service_account_info(info, scopes=[FCM_SCOPE])
    credentials.refresh(GoogleAuthRequest())
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "").strip() or info.get("project_id")
    if not project_id:
        raise ValueError("Firebase service-account project_id is missing.")
    return credentials.token, project_id


def send_pending_invoice_notification(invoice):
    """Notify the linked recipient's registered Android devices, if configured."""
    if not isinstance(invoice, Invoice) or invoice.pending_amount <= 0:
        return 0

    user_id = invoice.recipient_user_id
    if not user_id:
        recipient = User.query.filter(func.lower(User.email) == invoice.recipient_email.strip().lower()).first()
        user_id = recipient.id if recipient else None
    if not user_id:
        return 0

    devices = MobilePushDevice.query.filter_by(user_id=user_id).all()
    if not devices:
        return 0

    access_token, project_id = _access_token()
    if not access_token:
        logger.info("Skipping invoice push: Firebase server credentials are not configured.")
        return 0

    endpoint = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    message = {
        "data": {
            "type": "invoice_pending",
            "invoice_id": str(invoice.id),
            "invoice_number": str(invoice.invoice_number)[:80],
            "pending_amount": f"{invoice.pending_amount:.2f}",
        },
        "android": {"priority": "HIGH", "ttl": "86400s"},
    }
    delivered = 0
    for device in devices:
        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"message": {**message, "fid": device.installation_id}},
            timeout=8,
        )
        if response.ok:
            delivered += 1
            continue
        try:
            body = response.json() if response.content else {}
        except ValueError:
            body = {}
        error = (body.get("error") or {})
        details = error.get("details") or []
        error_codes = {str(item.get("errorCode", "")) for item in details if isinstance(item, dict)}
        if error.get("status") == "NOT_FOUND" or "UNREGISTERED" in error_codes:
            db.session.delete(device)
            db.session.flush()
        else:
            logger.warning(
                "FCM invoice push failed for device record %s (HTTP %s, %s).",
                device.id, response.status_code, error.get("status", "unknown"),
            )
    return delivered
