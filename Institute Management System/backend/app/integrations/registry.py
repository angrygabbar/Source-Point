"""Provider registry and configuration access for optional external integrations.

Nothing here simulates success: if a provider is not configured/enabled, callers receive
`None` / IntegrationUnavailable and must surface that state to users.
"""

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_secret
from app.models import IntegrationConfig

PROVIDERS: dict[str, dict[str, dict[str, Any]]] = {
    "email": {
        "smtp": {
            "label": "SMTP server",
            "config": ["host", "port", "username", "from_address", "use_tls"],
            "secrets": ["password"],
        },
    },
    "sms": {
        "msg91": {"label": "MSG91 (India, DLT flow)", "config": ["sender_id", "flow_id"], "secrets": ["auth_key"]},
        "twilio": {"label": "Twilio", "config": ["account_sid", "from_number"], "secrets": ["auth_token"]},
    },
    "whatsapp": {
        "meta_whatsapp": {
            "label": "WhatsApp Business Cloud API (Meta)",
            "config": ["phone_number_id", "default_template", "template_language"],
            "secrets": ["access_token"],
        },
    },
    "push": {
        "webpush": {"label": "Web Push (VAPID)", "config": ["vapid_public_key", "vapid_subject"], "secrets": ["vapid_private_key"]},
    },
    "payment": {
        "razorpay": {"label": "Razorpay", "config": ["key_id"], "secrets": ["key_secret", "webhook_secret"]},
    },
    "ai": {
        "openai_compatible": {
            "label": "OpenAI-compatible API",
            "config": ["base_url", "model", "monthly_token_limit", "input_cost_per_1k", "output_cost_per_1k"],
            "secrets": ["api_key"],
        },
    },
    "video": {
        "zoom": {"label": "Zoom (Server-to-Server OAuth)", "config": ["account_id", "client_id", "host_user"], "secrets": ["client_secret"]},
        "google_meet": {
            "label": "Google Meet (Calendar API)",
            "config": ["client_id", "calendar_id"],
            "secrets": ["client_secret", "refresh_token"],
        },
    },
}


@dataclass
class ProviderConfig:
    provider_type: str
    provider: str
    config: dict[str, Any]
    secrets: dict[str, Any]
    record: IntegrationConfig | None


def get_active(db: Session, institute_id: uuid.UUID | None, provider_type: str) -> ProviderConfig | None:
    if institute_id is not None:
        row = db.scalar(
            select(IntegrationConfig).where(
                IntegrationConfig.institute_id == institute_id,
                IntegrationConfig.provider_type == provider_type,
                IntegrationConfig.is_enabled.is_(True),
            )
        )
        if row:
            raw = decrypt_secret(row.secrets_encrypted)
            secrets = json.loads(raw) if raw else {}
            return ProviderConfig(provider_type, row.provider, dict(row.config or {}), secrets, row)
    # Platform-level fallbacks from environment variables.
    if provider_type == "email" and settings.SMTP_HOST and settings.SMTP_FROM:
        return ProviderConfig(
            "email",
            "smtp",
            {
                "host": settings.SMTP_HOST,
                "port": settings.SMTP_PORT,
                "username": settings.SMTP_USERNAME,
                "from_address": settings.SMTP_FROM,
                "use_tls": settings.SMTP_USE_TLS,
            },
            {"password": settings.SMTP_PASSWORD},
            None,
        )
    if provider_type == "push" and settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY:
        return ProviderConfig(
            "push",
            "webpush",
            {"vapid_public_key": settings.VAPID_PUBLIC_KEY, "vapid_subject": settings.VAPID_SUBJECT},
            {"vapid_private_key": settings.VAPID_PRIVATE_KEY},
            None,
        )
    return None
