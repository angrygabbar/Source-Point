from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import PageParams, csv_list, get_current_user, page_params, page_response, paginate
from app.api.schemas import PreferencesIn
from app.api.serializers import notification_out
from app.config import get_settings
from app.database.enums import NotificationEvent, NotificationStatus
from app.database.models import Notification, Product
from app.database.session import get_db
from app.notifications.service import get_preferences, queue_test

router = APIRouter(prefix="/api/notifications", tags=["notifications"], dependencies=[Depends(get_current_user)])
STATUSES = {s.value for s in NotificationStatus}
EVENTS = {e.value for e in NotificationEvent}


def _prefs_out(db: Session) -> dict:
    prefs = get_preferences(db)
    settings = get_settings()
    return {
        "enabled": prefs.enabled,
        "paused": prefs.paused,
        "min_percentage": prefs.min_percentage,
        "verified_only": prefs.verified_only,
        "include_unverified": prefs.include_unverified,
        "notify_new": prefs.notify_new,
        "notify_changes": prefs.notify_changes,
        "notify_expiring": prefs.notify_expiring,
        "updated_at": prefs.updated_at,
        "telegram": {
            "configured": settings.telegram_configured,
            "dry_run": settings.telegram_dry_run or not settings.telegram_bot_token,
            "commands_enabled": settings.telegram_commands_enabled,
            "chat_id_hint": f"…{settings.telegram_chat_id[-4:]}" if settings.telegram_chat_id else None,
        },
    }


@router.get("")
def list_notifications(
    status_: str | None = Query(None, alias="status", max_length=200),
    event_type: str | None = Query(None, max_length=200),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(Notification, Product.title).outerjoin(Product, Product.id == Notification.product_id)
    statuses = csv_list(status_, STATUSES)
    events = csv_list(event_type, EVENTS)
    if statuses:
        stmt = stmt.where(Notification.status.in_(statuses))
    if events:
        stmt = stmt.where(Notification.event_type.in_(events))
    rows, total = paginate(db, stmt.order_by(Notification.created_at.desc()), params)
    return page_response([notification_out(n, title) for n, title in rows], total, params)


@router.post("/test", status_code=status.HTTP_202_ACCEPTED)
def test_notification(db: Session = Depends(get_db)) -> dict:
    notification = queue_test(db)
    return {"data": {**notification_out(notification), "note": "Queued. The scanner delivers it (dry-run unless live delivery is enabled)."}}


@router.get("/preferences")
def get_prefs(db: Session = Depends(get_db)) -> dict:
    data = _prefs_out(db)
    db.commit()
    return {"data": data}


@router.put("/preferences")
def put_prefs(payload: PreferencesIn, db: Session = Depends(get_db)) -> dict:
    prefs = get_preferences(db)
    for key, value in payload.model_dump().items():
        setattr(prefs, key, Decimal(value) if key == "min_percentage" and value is not None else value)
    db.commit()
    return {"data": _prefs_out(db)}
