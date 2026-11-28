import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.logging import request_id_var
from app.models import AuditLog

if TYPE_CHECKING:
    from app.api.deps import Principal

_SKIP = {"password_hash", "secrets_encrypted", "secret_encrypted", "key_hash", "token_hash", "updated_at", "created_at"}


def jsonable(value: Any) -> Any:
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    return value


def snapshot(obj: Any) -> dict[str, Any]:
    mapper = inspect(obj).mapper
    return {c.key: jsonable(getattr(obj, c.key)) for c in mapper.column_attrs if c.key not in _SKIP}


def diff(old: dict[str, Any], new: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    keys = {k for k in set(old) | set(new) if old.get(k) != new.get(k)}
    return {k: old.get(k) for k in keys}, {k: new.get(k) for k in keys}


def record(
    db: Session,
    principal: "Principal | None",
    entity_type: str,
    entity_id: uuid.UUID | None,
    action: str,
    old: dict | None = None,
    new: dict | None = None,
    reason: str | None = None,
    institute_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
) -> None:
    db.add(
        AuditLog(
            institute_id=institute_id or (principal.institute_id if principal else None),
            branch_id=branch_id,
            actor_id=principal.user_id if principal else None,
            actor_email=principal.user.email if principal and principal.user else None,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_values=jsonable(old or {}),
            new_values=jsonable(new or {}),
            reason=reason,
            ip_address=principal.ip_address if principal else None,
            request_id=request_id_var.get(),
        )
    )
