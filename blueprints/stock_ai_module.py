"""SourcePoint gateway for the admin and developer Stock AI module."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import requests
from flask import Blueprint, Response, current_app, jsonify, redirect, request, url_for
from flask_login import current_user

from enums import UserRole

stock_ai_module_bp = Blueprint("stock_ai_module", __name__)

_ALLOWED_ROLES = {UserRole.ADMIN.value, UserRole.DEVELOPER.value}
_METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _sourcepoint_token() -> str | None:
    secret = current_app.config.get("STOCK_AI_SSO_SECRET")
    if not secret or len(secret.encode("utf-8")) < 32:
        current_app.logger.error("STOCK_AI_SSO_SECRET must contain at least 32 bytes")
        return None

    issued_at = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": "sourcepoint",
        "aud": "stock-ai",
        "sub": str(current_user.id),
        "sourcepoint_user_id": int(current_user.id),
        "username": current_user.username,
        "role": current_user.role,
        "iat": issued_at,
        "exp": issued_at + 120,
    }
    signing_input = f"{_encode(json.dumps(header, separators=(',', ':')).encode())}.{_encode(json.dumps(payload, separators=(',', ':')).encode())}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_encode(signature)}"


def _is_api_request() -> bool:
    return request.path.startswith("/stock-ai/api/") or request.path.startswith("/stock-ai/socket.io")


def _access_error():
    api = _is_api_request()
    if not current_user.is_authenticated:
        if api:
            return jsonify({"error": "Sign in to SourcePoint to continue."}), 401
        return redirect(url_for("auth.login_register", next=request.full_path))

    if (
        not current_user.is_active
        or not current_user.is_approved
        or current_user.role not in _ALLOWED_ROLES
    ):
        if api:
            return jsonify({"error": "Stock AI is available to SourcePoint administrators and developers only."}), 403
        return "Stock AI is available to SourcePoint administrators and developers only.", 403

    return None


def _proxy(upstream_path: str) -> Response | tuple[Response, int] | str | tuple[str, int]:
    denied = _access_error()
    if denied is not None:
        return denied

    base_url = (current_app.config.get("STOCK_AI_URL") or "").rstrip("/")
    if not base_url:
        message = "Stock AI is not configured."
        if _is_api_request():
            return jsonify({"error": message}), 503
        return message, 503

    target_url = f"{base_url}{upstream_path}"
    if request.query_string:
        target_url = f"{target_url}?{request.query_string.decode('latin-1')}"

    forwarded_headers = {}
    for name in (
        "Accept",
        "Content-Type",
        "Range",
        "If-None-Match",
        "If-Modified-Since",
        "X-Requested-With",
        "Origin",
    ):
        value = request.headers.get(name)
        if value:
            forwarded_headers[name] = value

    forwarded_headers.update(
        {
            "X-Forwarded-Host": request.headers.get("X-Forwarded-Host", request.host),
            "X-Forwarded-Proto": request.headers.get("X-Forwarded-Proto", request.scheme),
            "X-Forwarded-Prefix": "/stock-ai",
        }
    )

    token = _sourcepoint_token()
    if token is None:
        message = "Stock AI sign-in is not configured."
        if _is_api_request():
            return jsonify({"error": message}), 503
        return message, 503
    forwarded_headers["Authorization"] = f"Bearer {token}"

    try:
        upstream = requests.request(
            method=request.method,
            url=target_url,
            headers=forwarded_headers,
            data=request.get_data(),
            timeout=(5, 120),
            allow_redirects=False,
        )
    except requests.RequestException:
        current_app.logger.exception("Stock AI upstream request failed")
        message = "Stock AI is temporarily unavailable."
        if _is_api_request():
            return jsonify({"error": message}), 502
        return message, 502

    response_headers = {}
    for name in ("Content-Type", "Content-Disposition", "Cache-Control", "ETag", "Last-Modified", "Location"):
        value = upstream.headers.get(name)
        if value:
            if name == "Location" and value.startswith("/") and not value.startswith("/stock-ai/"):
                value = f"/stock-ai{value}"
            response_headers[name] = value

    # Keep the SourcePoint session cookie private to SourcePoint. Stock AI has no
    # login cookie; every browser request is authorized again by this gateway.
    response_headers.setdefault("Cache-Control", "private, no-store")
    return Response(upstream.content, status=upstream.status_code, headers=response_headers)


@stock_ai_module_bp.route("/stock-ai", defaults={"path": ""}, methods=_METHODS)
@stock_ai_module_bp.route("/stock-ai/", defaults={"path": ""}, methods=_METHODS)
def home(path: str = ""):
    """Open Stock AI on its dashboard inside SourcePoint."""
    return _proxy("/dashboard")


@stock_ai_module_bp.route("/stock-ai/<path:path>", methods=_METHODS)
def module_path(path: str):
    """Proxy a Stock AI page, API request, or Socket.IO polling request."""
    return _proxy(f"/{path}")
