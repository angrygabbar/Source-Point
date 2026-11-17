"""Notification rules, event de-duplication, queueing and delivery with retries."""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.enums import INACTIVE_OFFER_STATUSES, NotificationEvent, NotificationStatus, OfferStatus
from app.database.models import Notification, NotificationPreference, Offer, Product
from app.notifications.formatter import offer_message
from app.notifications.telegram import TelegramClient
from app.services.clock import format_ist, utcnow

logger = logging.getLogger(__name__)
MAX_RETRIES = 5


def get_preferences(db: Session) -> NotificationPreference:
    prefs = db.scalar(select(NotificationPreference).where(NotificationPreference.scope == "global"))
    if prefs is None:
        prefs = NotificationPreference(scope="global")
        db.add(prefs)
        db.flush()
    return prefs


def offer_qualifies(offer: Offer, prefs: NotificationPreference) -> bool:
    if offer.status in INACTIVE_OFFER_STATUSES:
        return False
    if prefs.verified_only and offer.status != OfferStatus.VERIFIED:
        return False
    if not prefs.include_unverified and offer.status != OfferStatus.VERIFIED:
        return False
    if prefs.min_percentage is not None:
        if offer.advertised_percentage is None or offer.advertised_percentage < prefs.min_percentage:
            return False
    return True


def _event_key(event: str, offer: Offer) -> str:
    if event == NotificationEvent.NEW_OFFER:
        return f"NEW_OFFER:{offer.id}"
    if event == NotificationEvent.OFFER_EXPIRING:
        return f"OFFER_EXPIRING:{offer.id}:{offer.valid_until.date() if offer.valid_until else 'na'}"
    state = f"{offer.advertised_percentage}|{offer.advertised_coins}|{offer.reward_cap_coins}|{offer.per_spend_coins}|{offer.status}"
    return f"{event}:{offer.id}:{hashlib.sha256(state.encode()).hexdigest()[:24]}"


def _queue(db: Session, *, event: str, key: str, message: str, offer: Offer | None, product: Product | None,
           chat_id: str | None) -> bool:
    stmt = (
        insert(Notification)
        .values(
            id=uuid.uuid4(),
            product_id=product.id if product else None,
            offer_id=offer.id if offer else None,
            channel="telegram",
            chat_id=chat_id,
            event_type=event,
            event_key=key,
            message=message,
            status=NotificationStatus.PENDING,
            next_attempt_at=utcnow(),
        )
        .on_conflict_do_nothing(index_elements=["event_key"])
        .returning(Notification.id)
    )
    return db.execute(stmt).scalar() is not None


def queue_offer_events(db: Session, new_ids: Iterable[uuid.UUID], changed_ids: Iterable[uuid.UUID]) -> int:
    prefs = get_preferences(db)
    if not prefs.enabled:
        return 0
    chat_id = get_settings().telegram_chat_id
    queued = 0
    plan = []
    if prefs.notify_new:
        plan += [(NotificationEvent.NEW_OFFER, oid) for oid in new_ids]
    if prefs.notify_changes:
        plan += [(NotificationEvent.OFFER_CHANGED, oid) for oid in changed_ids]
    for event, offer_id in plan:
        offer = db.get(Offer, offer_id)
        if offer is None or not offer_qualifies(offer, prefs):
            continue
        product = offer.product
        if _queue(db, event=event, key=_event_key(event, offer), message=offer_message(event, offer, product),
                  offer=offer, product=product, chat_id=chat_id):
            queued += 1
    return queued


def queue_expiring(db: Session, now: datetime, within_hours: int = 24) -> int:
    prefs = get_preferences(db)
    if not (prefs.enabled and prefs.notify_expiring):
        return 0
    chat_id = get_settings().telegram_chat_id
    offers = db.scalars(
        select(Offer).where(
            Offer.status.notin_(INACTIVE_OFFER_STATUSES),
            Offer.valid_until.is_not(None),
            Offer.valid_until > now,
            Offer.valid_until <= now + timedelta(hours=within_hours),
        )
    ).all()
    queued = 0
    for offer in offers:
        if offer_qualifies(offer, prefs) and _queue(
            db, event=NotificationEvent.OFFER_EXPIRING, key=_event_key(NotificationEvent.OFFER_EXPIRING, offer),
            message=offer_message(NotificationEvent.OFFER_EXPIRING, offer, offer.product), offer=offer,
            product=offer.product, chat_id=chat_id,
        ):
            queued += 1
    return queued


def queue_test(db: Session) -> Notification:
    settings = get_settings()
    key = f"TEST:{uuid.uuid4()}"
    message = (
        "<b>CoinBack Finder test notification</b>\n"
        f"Queued: {format_ist(utcnow())}\n"
        "Delivery channel configuration check. No offer data included."
    )
    _queue(db, event=NotificationEvent.TEST, key=key, message=message, offer=None, product=None,
           chat_id=settings.telegram_chat_id)
    db.commit()
    return db.scalar(select(Notification).where(Notification.event_key == key))


def dispatch_pending(db: Session, client: TelegramClient, settings: Settings | None = None, batch: int = 20) -> dict[str, int]:
    settings = settings or get_settings()
    now = utcnow()
    prefs = get_preferences(db)
    counts = {"sent": 0, "dry_run": 0, "failed": 0, "suppressed": 0}
    rows = db.scalars(
        select(Notification)
        .where(
            Notification.status.in_((NotificationStatus.PENDING, NotificationStatus.FAILED)),
            Notification.retry_count < MAX_RETRIES,
            or_(Notification.next_attempt_at.is_(None), Notification.next_attempt_at <= now),
        )
        .order_by(Notification.created_at)
        .limit(batch)
        .with_for_update(skip_locked=True)
    ).all()

    for n in rows:
        is_test = n.event_type == NotificationEvent.TEST
        if not is_test and (prefs.paused or not prefs.enabled):
            n.status = NotificationStatus.SUPPRESSED
            n.last_error = "Notifications paused." if prefs.paused else "Notifications disabled."
            counts["suppressed"] += 1
            continue
        chat_id = n.chat_id or settings.telegram_chat_id
        if not client.dry_run and not chat_id:
            n.status = NotificationStatus.FAILED
            n.retry_count = MAX_RETRIES
            n.last_error = "TELEGRAM_CHAT_ID is not configured."
            counts["failed"] += 1
            continue
        result = client.send_message(chat_id or "dry-run", n.message)
        if result.ok:
            n.status = NotificationStatus.DRY_RUN if result.dry_run else NotificationStatus.SENT
            n.sent_at = now
            n.last_error = "Dry-run mode: message not delivered." if result.dry_run else None
            counts["dry_run" if result.dry_run else "sent"] += 1
        else:
            n.retry_count += 1
            n.status = NotificationStatus.FAILED
            n.last_error = result.error
            delay = result.retry_after or min(60 * 2 ** n.retry_count, 3600)
            n.next_attempt_at = now + timedelta(seconds=delay)
            counts["failed"] += 1
    db.commit()
    return counts
