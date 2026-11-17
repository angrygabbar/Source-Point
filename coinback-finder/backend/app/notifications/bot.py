"""Telegram command handling via long-poll getUpdates. Only the configured chat is answered."""

from __future__ import annotations

import logging
from html import escape

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.enums import INACTIVE_OFFER_STATUSES, OfferStatus, ScanStatus
from app.database.models import MonitoredProduct, Offer, Product, ScanRun
from app.notifications.formatter import STATUS_LABEL, format_inr, format_pct
from app.notifications.service import get_preferences
from app.notifications.telegram import TelegramClient
from app.services.clock import format_ist, ist_day_start_utc, utcnow
from app.services.settings_store import get_value, set_value

logger = logging.getLogger(__name__)
LIST_LIMIT = 10

HELP = (
    "<b>CoinBack Finder</b>\n"
    "/deals – top active offers by advertised %\n"
    "/100 – active offers at 100% or above\n"
    "/all – summary and latest offers\n"
    "/today – offers detected today (IST)\n"
    "/stats – scanner and data statistics\n"
    "/pause – pause alerts\n"
    "/resume – resume alerts\n\n"
    "Advertised values only. Verify eligibility in your own account before purchase."
)


def _active_offers():
    now = utcnow()
    return (
        select(Offer, Product)
        .join(Product, Product.id == Offer.product_id)
        .where(
            Offer.status.notin_(INACTIVE_OFFER_STATUSES),
            Product.archived_at.is_(None),
            (Offer.valid_until.is_(None)) | (Offer.valid_until > now),
        )
    )


def _render(rows) -> str:
    if not rows:
        return "No matching offers."
    lines = []
    for i, (offer, product) in enumerate(rows, 1):
        pct = format_pct(offer.advertised_percentage)
        if offer.is_up_to and offer.advertised_percentage is not None:
            pct = f"up to {pct}"
        lines.append(
            f"{i}. {escape((product.title or 'Untitled')[:80])}\n"
            f"   {format_inr(product.current_price)} · {escape(pct)} · {STATUS_LABEL.get(offer.status, offer.status)}\n"
            f"   {escape(product.product_url)}"
        )
    return "\n".join(lines)


def handle_command(db: Session, command: str) -> str:
    order = (Offer.advertised_percentage.desc().nulls_last(), Offer.last_seen_at.desc())
    if command in ("/start", "/help"):
        return HELP
    if command == "/deals":
        rows = db.execute(_active_offers().order_by(*order).limit(LIST_LIMIT)).all()
        return "<b>Top active offers</b>\n" + _render(rows)
    if command == "/100":
        rows = db.execute(_active_offers().where(Offer.advertised_percentage >= 100).order_by(*order).limit(LIST_LIMIT)).all()
        return "<b>Offers at 100%+ (advertised)</b>\n" + _render(rows)
    if command == "/all":
        total = db.scalar(select(func.count()).select_from(_active_offers().subquery()))
        rows = db.execute(_active_offers().order_by(Offer.first_detected_at.desc()).limit(LIST_LIMIT)).all()
        return f"<b>{total} active offers</b> (latest {min(LIST_LIMIT, len(rows))})\n" + _render(rows)
    if command == "/today":
        rows = db.execute(
            _active_offers().where(Offer.first_detected_at >= ist_day_start_utc()).order_by(*order).limit(LIST_LIMIT)
        ).all()
        return "<b>Detected today</b>\n" + _render(rows)
    if command == "/stats":
        active = db.scalar(select(func.count()).select_from(_active_offers().subquery())) or 0
        hundred = db.scalar(select(func.count()).select_from(_active_offers().where(Offer.advertised_percentage >= 100).subquery())) or 0
        verified = db.scalar(select(func.count()).select_from(_active_offers().where(Offer.status == OfferStatus.VERIFIED).subquery())) or 0
        products = db.scalar(select(func.count()).select_from(Product).where(Product.archived_at.is_(None))) or 0
        monitored = db.scalar(select(func.count()).select_from(MonitoredProduct).where(MonitoredProduct.enabled.is_(True))) or 0
        last = db.scalar(select(ScanRun).where(ScanRun.status.in_((ScanStatus.SUCCEEDED, ScanStatus.PARTIAL))).order_by(ScanRun.finished_at.desc()).limit(1))
        prefs = get_preferences(db)
        return (
            "<b>Statistics</b>\n"
            f"Products: {products}\nMonitored: {monitored}\nActive offers: {active}\n100%+ offers: {hundred}\n"
            f"Verified: {verified}\nLast successful scan: {format_ist(last.finished_at) if last else 'Not available'}\n"
            f"Alerts: {'paused' if prefs.paused else 'active'}"
        )
    if command in ("/pause", "/resume"):
        prefs = get_preferences(db)
        prefs.paused = command == "/pause"
        db.commit()
        return "Alerts paused." if prefs.paused else "Alerts resumed."
    return "Unknown command. Send /start for the list of commands."


def poll_commands(db: Session, client: TelegramClient, settings: Settings) -> int:
    if client.dry_run or not settings.telegram_chat_id:
        return 0
    offset = int(get_value(db, "telegram_update_offset", 0) or 0)
    handled = 0
    for update in client.get_updates(offset):
        offset = max(offset, int(update.get("update_id", 0)) + 1)
        message = update.get("message") or {}
        chat_id = str((message.get("chat") or {}).get("id", ""))
        text = (message.get("text") or "").strip()
        if chat_id != str(settings.telegram_chat_id) or not text.startswith("/"):
            continue
        command = text.split()[0].split("@")[0].lower()
        try:
            reply = handle_command(db, command)
        except Exception:
            logger.exception("Telegram command %s failed", command)
            db.rollback()
            reply = "Command failed. Check scanner logs."
        client.send_message(chat_id, reply)
        handled += 1
    set_value(db, "telegram_update_offset", offset)
    db.commit()
    return handled
