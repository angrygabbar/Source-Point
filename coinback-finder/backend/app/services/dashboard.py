"""Dashboard metrics, analytics and scanner status. All values come from stored data."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import Integer, case, cast, func, select
from sqlalchemy.orm import Session, contains_eager

from app.api.serializers import notification_out, offer_full, scan_run_out, source_out
from app.database.enums import PENDING_VERIFICATION_STATUSES, OfferStatus, ScanStatus
from app.database.models import DiscoverySource, MonitoredProduct, Notification, Offer, PriceHistory, Product, ScanRun
from app.services.clock import IST, ist_day_start_utc, utcnow
from app.services.queries import active_offer_clause
from app.services.settings_store import get_value

TZ_NAME = "Asia/Kolkata"


def _count(db: Session, stmt) -> int:
    return int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)


def _active_offers():
    return select(Offer.id).join(Product, Product.id == Offer.product_id).where(Product.archived_at.is_(None), active_offer_clause())


def _ist_date(column):
    return func.date(func.timezone(TZ_NAME, column))


def _days(start: datetime, end: datetime) -> list[date]:
    first, last = start.astimezone(IST).date(), end.astimezone(IST).date()
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def summary(db: Session) -> dict[str, Any]:
    now = utcnow()
    today = ist_day_start_utc(now)
    yesterday = today - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    finished = db.execute(
        select(ScanRun.status, func.count()).where(
            ScanRun.started_at >= week_ago,
            ScanRun.status.in_((ScanStatus.SUCCEEDED, ScanStatus.PARTIAL, ScanStatus.FAILED, ScanStatus.INTERRUPTED)),
        ).group_by(ScanRun.status)
    ).all()
    by_status = {s: c for s, c in finished}
    total_finished = sum(by_status.values())

    return {
        "total_products": _count(db, select(Product.id).where(Product.archived_at.is_(None))),
        "active_offers": _count(db, _active_offers()),
        "offers_100_plus": _count(db, _active_offers().where(Offer.advertised_percentage >= 100)),
        "verified_offers": _count(db, _active_offers().where(Offer.status == OfferStatus.VERIFIED)),
        "awaiting_verification": _count(db, _active_offers().where(Offer.status.in_(PENDING_VERIFICATION_STATUSES))),
        "monitored_products": _count(db, select(MonitoredProduct.id).join(Product).where(MonitoredProduct.enabled.is_(True), Product.archived_at.is_(None))),
        "today_discoveries": _count(db, select(Offer.id).where(Offer.first_detected_at >= today)),
        "yesterday_discoveries": _count(db, select(Offer.id).where(Offer.first_detected_at >= yesterday, Offer.first_detected_at < today)),
        "today_new_products": _count(db, select(Product.id).where(Product.first_seen_at >= today)),
        "scanner_success_rate": round(by_status.get(ScanStatus.SUCCEEDED, 0) / total_finished * 100, 1) if total_finished else None,
        "scanner_runs_7d": total_finished,
        "scanner_runs_by_status_7d": by_status,
        "generated_at": now,
    }


def panels(db: Session, limit: int = 8) -> dict[str, Any]:
    def offers(stmt) -> list[dict[str, Any]]:
        return [offer_full(o) for o in db.scalars(stmt.limit(limit)).unique().all()]

    base = (
        select(Offer).join(Product, Product.id == Offer.product_id).options(contains_eager(Offer.product))
        .where(Product.archived_at.is_(None))
    )
    active = base.where(active_offer_clause())
    notifications = db.execute(
        select(Notification, Product.title).outerjoin(Product, Product.id == Notification.product_id)
        .order_by(Notification.created_at.desc()).limit(limit)
    ).all()

    return {
        "latest_deals": offers(active.order_by(Offer.first_detected_at.desc())),
        "highest_rewards": offers(active.where(Offer.advertised_percentage.is_not(None)).order_by(Offer.advertised_percentage.desc(), Offer.estimated_coins.desc().nulls_last())),
        "recently_changed": offers(base.where(Offer.last_changed_at > Offer.first_detected_at).order_by(Offer.last_changed_at.desc())),
        "expiring": offers(active.where(Offer.valid_until.is_not(None)).order_by(Offer.valid_until.asc())),
        "scanner_activity": [scan_run_out(r) for r in db.scalars(select(ScanRun).order_by(ScanRun.queued_at.desc()).limit(limit)).all()],
        "recent_notifications": [notification_out(n, title) for n, title in notifications],
    }


def _bucket_counts(db: Session, buckets: list[tuple[str, Any]], else_label: str, where=None) -> list[dict[str, Any]]:
    label = case(*[(cond, name) for name, cond in buckets], else_=else_label).label("bucket")
    stmt = select(label, func.count()).select_from(Offer).join(Product, Product.id == Offer.product_id).where(
        Product.archived_at.is_(None), active_offer_clause()
    )
    if where is not None:
        stmt = stmt.where(where)
    rows = dict(db.execute(stmt.group_by(label)).all())
    order = [name for name, _ in buckets] + [else_label]
    return [{"bucket": name, "count": int(rows.get(name, 0))} for name in order]


def analytics(db: Session, start: datetime, end: datetime) -> dict[str, Any]:
    pct = Offer.advertised_percentage
    coinback_distribution = _bucket_counts(db, [
        ("Not calculated", pct.is_(None)),
        ("<10%", pct < 10),
        ("10–24%", pct < 25),
        ("25–49%", pct < 50),
        ("50–74%", pct < 75),
        ("75–99%", pct < 100),
        ("100%", pct == 100),
    ], ">100%")

    coins = func.coalesce(Offer.advertised_coins, Offer.estimated_coins)
    reward_distribution = _bucket_counts(db, [
        ("Unknown", coins.is_(None)),
        ("<100", coins < 100),
        ("100–249", coins < 250),
        ("250–499", coins < 500),
        ("500–999", coins < 1000),
        ("1,000–2,499", coins < 2500),
    ], "2,500+")

    now = utcnow()
    expiry = _bucket_counts(db, [
        ("No expiry stated", Offer.valid_until.is_(None)),
        ("< 24 h", Offer.valid_until <= now + timedelta(hours=24)),
        ("1–3 days", Offer.valid_until <= now + timedelta(days=3)),
        ("3–7 days", Offer.valid_until <= now + timedelta(days=7)),
    ], "> 7 days")

    days = _days(start, end)
    offer_day = _ist_date(Offer.first_detected_at)
    offers_by_day = dict(db.execute(
        select(offer_day, func.count()).where(Offer.first_detected_at >= start, Offer.first_detected_at <= end).group_by(offer_day)
    ).all())
    product_day = _ist_date(Product.first_seen_at)
    products_by_day = dict(db.execute(
        select(product_day, func.count()).where(Product.first_seen_at >= start, Product.first_seen_at <= end).group_by(product_day)
    ).all())
    reward_by_day = {
        d: (avg, mx) for d, avg, mx in db.execute(
            select(offer_day, func.avg(Offer.advertised_percentage), func.max(Offer.advertised_percentage))
            .where(Offer.first_detected_at >= start, Offer.first_detected_at <= end, Offer.advertised_percentage.is_not(None))
            .group_by(offer_day)
        ).all()
    }
    discovery_trend = [
        {
            "date": d.isoformat(),
            "offers": int(offers_by_day.get(d, 0)),
            "products": int(products_by_day.get(d, 0)),
            "avg_pct": float(reward_by_day[d][0]) if d in reward_by_day and reward_by_day[d][0] is not None else None,
            "max_pct": float(reward_by_day[d][1]) if d in reward_by_day and reward_by_day[d][1] is not None else None,
        }
        for d in days
    ]

    prev = func.lag(PriceHistory.selling_price).over(partition_by=PriceHistory.product_id, order_by=PriceHistory.captured_at)
    ph = (
        select(PriceHistory.captured_at, PriceHistory.selling_price, prev.label("prev"))
        .where(PriceHistory.captured_at >= start - timedelta(days=30), PriceHistory.captured_at <= end)
        .subquery()
    )
    ph_day = _ist_date(ph.c.captured_at)
    movement_rows = db.execute(
        select(
            ph_day,
            func.sum(cast(ph.c.selling_price < ph.c.prev, Integer)),
            func.sum(cast(ph.c.selling_price > ph.c.prev, Integer)),
        ).where(ph.c.captured_at >= start, ph.c.prev.is_not(None)).group_by(ph_day)
    ).all()
    movement = {d: (drops or 0, rises or 0) for d, drops, rises in movement_rows}
    price_movement = [{"date": d.isoformat(), "drops": int(movement.get(d, (0, 0))[0]), "rises": int(movement.get(d, (0, 0))[1])} for d in days]

    category = func.coalesce(Product.category, "Uncategorised")
    category_distribution = [
        {"category": c, "offers": int(n), "avg_pct": float(a) if a is not None else None}
        for c, n, a in db.execute(
            select(category, func.count(), func.avg(Offer.advertised_percentage))
            .select_from(Offer).join(Product, Product.id == Offer.product_id)
            .where(Product.archived_at.is_(None), active_offer_clause())
            .group_by(category).order_by(func.count().desc()).limit(12)
        ).all()
    ]

    status_breakdown = [
        {"status": s, "count": int(n)}
        for s, n in db.execute(
            select(Offer.status, func.count()).select_from(Offer).join(Product, Product.id == Offer.product_id)
            .where(Product.archived_at.is_(None), Offer.first_detected_at >= start).group_by(Offer.status)
        ).all()
    ]

    hour = cast(func.extract("hour", func.timezone(TZ_NAME, Offer.first_detected_at)), Integer)
    hours = dict(db.execute(
        select(hour, func.count()).where(Offer.first_detected_at >= start, Offer.first_detected_at <= end).group_by(hour)
    ).all())
    weekday = cast(func.extract("isodow", func.timezone(TZ_NAME, Offer.first_detected_at)), Integer)
    weekdays = dict(db.execute(
        select(weekday, func.count()).where(Offer.first_detected_at >= start, Offer.first_detected_at <= end).group_by(weekday)
    ).all())

    sources = db.scalars(select(DiscoverySource).order_by(DiscoverySource.name)).all()
    offers_by_source = dict(db.execute(
        select(Offer.source_id, func.count()).where(Offer.first_detected_at >= start).group_by(Offer.source_id)
    ).all())
    source_performance = [
        {**source_out(s), "offers_in_range": int(offers_by_source.get(s.id, 0))} for s in sources
    ]

    run_day = _ist_date(ScanRun.started_at)
    scan_rows = db.execute(
        select(
            run_day,
            func.count(),
            func.sum(cast(ScanRun.status == ScanStatus.FAILED, Integer)),
            func.avg(ScanRun.duration_ms),
            func.sum(ScanRun.products_processed),
            func.sum(ScanRun.offers_detected),
        ).where(ScanRun.started_at >= start, ScanRun.started_at <= end, ScanRun.status != ScanStatus.SKIPPED).group_by(run_day)
    ).all()
    scans = {d: (n, f, a, p, o) for d, n, f, a, p, o in scan_rows}
    scan_performance = [
        {
            "date": d.isoformat(),
            "runs": int(scans[d][0]) if d in scans else 0,
            "failed": int(scans[d][1] or 0) if d in scans else 0,
            "avg_duration_ms": float(scans[d][2]) if d in scans and scans[d][2] is not None else None,
            "products_processed": int(scans[d][3] or 0) if d in scans else 0,
            "offers_detected": int(scans[d][4] or 0) if d in scans else 0,
        }
        for d in days
    ]

    top = db.scalars(
        select(Offer).join(Product, Product.id == Offer.product_id).options(contains_eager(Offer.product))
        .where(Product.archived_at.is_(None), active_offer_clause(), Offer.advertised_percentage.is_not(None))
        .order_by(Offer.advertised_percentage.desc(), func.coalesce(Offer.advertised_coins, Offer.estimated_coins).desc().nulls_last())
        .limit(10)
    ).unique().all()

    return {
        "range": {"start": start, "end": end},
        "coinback_distribution": coinback_distribution,
        "reward_distribution": reward_distribution,
        "expiry_distribution": expiry,
        "discovery_trend": discovery_trend,
        "price_movement": price_movement,
        "category_distribution": category_distribution,
        "status_breakdown": status_breakdown,
        "detection_by_hour": [{"hour": h, "count": int(hours.get(h, 0))} for h in range(24)],
        "detection_by_weekday": [{"weekday": w, "count": int(weekdays.get(w, 0))} for w in range(1, 8)],
        "source_performance": source_performance,
        "scan_performance": scan_performance,
        "highest_rewards": [offer_full(o) for o in top],
    }


def scanner_status(db: Session) -> dict[str, Any]:
    now = utcnow()
    month_ago = now - timedelta(days=30)
    day_ago = now - timedelta(days=1)
    heartbeat = get_value(db, "scanner_heartbeat", {}) or {}
    schedule = get_value(db, "scanner_schedule", {}) or {}
    alive_at = schedule.get("alive_at")
    alive = False
    if alive_at:
        try:
            alive = now - datetime.fromisoformat(alive_at) < timedelta(minutes=2)
        except ValueError:
            alive = False

    current = db.scalar(select(ScanRun).where(ScanRun.status == ScanStatus.RUNNING).order_by(ScanRun.started_at.desc()).limit(1))
    last = db.scalar(select(ScanRun).where(ScanRun.finished_at.is_not(None), ScanRun.status != ScanStatus.SKIPPED).order_by(ScanRun.finished_at.desc()).limit(1))
    last_success = db.scalar(select(ScanRun).where(ScanRun.status == ScanStatus.SUCCEEDED).order_by(ScanRun.finished_at.desc()).limit(1))
    totals = db.execute(
        select(
            func.count(),
            func.sum(cast(ScanRun.status == ScanStatus.FAILED, Integer)),
            func.avg(ScanRun.duration_ms),
        ).where(ScanRun.queued_at >= month_ago, ScanRun.status.notin_((ScanStatus.QUEUED, ScanStatus.SKIPPED)))
    ).one()
    day = db.execute(
        select(func.coalesce(func.sum(ScanRun.products_processed), 0), func.coalesce(func.sum(ScanRun.offers_detected), 0))
        .where(ScanRun.started_at >= day_ago)
    ).one()
    sources = db.scalars(select(DiscoverySource).order_by(DiscoverySource.name)).all()

    if not alive:
        state = "offline"
    elif current is not None:
        state = "running"
    else:
        state = "idle"

    return {
        "state": state,
        "alive": alive,
        "alive_at": alive_at,
        "next_scan_at": schedule.get("next_scan_at"),
        "interval_minutes": schedule.get("interval_minutes"),
        "scanner_enabled": schedule.get("scanner_enabled"),
        "telegram_mode": schedule.get("telegram_mode"),
        "heartbeat": heartbeat,
        "current_run": scan_run_out(current) if current else None,
        "last_run": scan_run_out(last) if last else None,
        "last_success_at": last_success.finished_at if last_success else None,
        "queued_runs": _count(db, select(ScanRun.id).where(ScanRun.status == ScanStatus.QUEUED)),
        "runs_30d": int(totals[0] or 0),
        "failed_30d": int(totals[1] or 0),
        "avg_duration_ms_30d": float(totals[2]) if totals[2] is not None else None,
        "products_processed_24h": int(day[0]),
        "offers_detected_24h": int(day[1]),
        "sources": [source_out(s) for s in sources],
    }
