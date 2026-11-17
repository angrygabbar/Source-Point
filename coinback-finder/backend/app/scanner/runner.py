"""Scan cycle orchestration: discovery, monitoring, expiry and notification queueing."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.connectors.base import AccessBlocked, AccessNotPermitted, ConnectorError, DiscoveryContext, RateLimited
from app.connectors.http import SafeHttpClient
from app.connectors.registry import build_connector
from app.database.enums import (
    AccessStatus,
    NotificationStatus,
    OfferStatus,
    ScanStatus,
    ScanTrigger,
    SourceType,
)
from app.database.models import DiscoverySource, MonitoredProduct, Notification, Offer, Product, ScanRun
from app.database.session import session_scope
from app.notifications.service import queue_expiring, queue_offer_events
from app.scanner.lock import advisory_lock
from app.scanner.rate_limit import RateLimiter
from app.services.clock import format_ist, utcnow
from app.services.ingestion import IngestOutcome, add_snapshot, ingest_observation
from app.services.settings_store import AppConfig, get_app_config, get_value, set_value

logger = logging.getLogger(__name__)

MAX_MONITORED_PER_RUN = 200
MAX_LOG_ENTRIES = 500
UNAVAILABLE_AFTER_FAILURES = 3
PAGE_CONNECTOR = "flipkart_product_page"


class RunLog:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def add(self, level: str, message: str, source: str | None = None) -> None:
        level_no = {"debug": logging.DEBUG, "warning": logging.WARNING, "error": logging.ERROR}.get(level, logging.INFO)
        logger.log(level_no, "%s%s", f"[{source}] " if source else "", message)
        if len(self.entries) < MAX_LOG_ENTRIES:
            self.entries.append({"ts": utcnow().isoformat(), "level": level, "source": source, "message": message[:1000]})


@dataclass
class RunStats:
    products_discovered: int = 0
    products_processed: int = 0
    offers_detected: int = 0
    offers_new: int = 0
    offers_expired: int = 0
    notifications_queued: int = 0
    errors: int = 0
    sources_ok: int = 0
    sources_failed: int = 0
    sources_skipped: int = 0
    new_offer_ids: list[uuid.UUID] = field(default_factory=list)
    changed_offer_ids: list[uuid.UUID] = field(default_factory=list)
    source_results: list[dict[str, Any]] = field(default_factory=list)

    def absorb(self, outcome: IngestOutcome) -> None:
        if outcome.skipped_reason:
            return
        self.products_processed += 1
        self.products_discovered += int(outcome.product_created)
        self.offers_detected += outcome.offers_detected
        self.offers_new += len(outcome.new_offer_ids)
        self.new_offer_ids.extend(outcome.new_offer_ids)
        self.changed_offer_ids.extend(outcome.changed_offer_ids)


def write_heartbeat(db: Session, **fields: Any) -> None:
    current = get_value(db, "scanner_heartbeat", {}) or {}
    current.update({k: (v.isoformat() if isinstance(v, datetime) else str(v) if isinstance(v, uuid.UUID) else v) for k, v in fields.items()})
    current["updated_at"] = utcnow().isoformat()
    set_value(db, "scanner_heartbeat", current)


class ScanRunner:
    def __init__(self, settings: Settings, stop_event: threading.Event) -> None:
        self.settings = settings
        self.stop = stop_event
        self.http = SafeHttpClient(settings)
        self._limiters: dict[str, RateLimiter] = {}

    def close(self) -> None:
        self.http.close()

    def _limiter(self, source_id: uuid.UUID, per_minute: int) -> RateLimiter:
        key = f"{source_id}:{per_minute}"
        if key not in self._limiters:
            self._limiters[key] = RateLimiter(per_minute)
        return self._limiters[key]

    # ---- lifecycle -------------------------------------------------------------------------
    def recover_interrupted(self) -> None:
        with advisory_lock() as acquired:
            if not acquired:
                return
            with session_scope() as db:
                for run in db.scalars(select(ScanRun).where(ScanRun.status == ScanStatus.RUNNING)).all():
                    run.status = ScanStatus.INTERRUPTED
                    run.finished_at = utcnow()
                    run.details = {**(run.details or {}), "recovery": "Marked interrupted after scanner restart."}
                write_heartbeat(db, state="idle", current_run_id=None)

    def run_queued(self) -> None:
        with session_scope() as db:
            ids = db.scalars(select(ScanRun.id).where(ScanRun.status == ScanStatus.QUEUED).order_by(ScanRun.queued_at)).all()
        for run_id in ids:
            if self.stop.is_set():
                break
            self.run_cycle(ScanTrigger.MANUAL, run_id=run_id)

    def run_cycle(self, trigger: str, run_id: uuid.UUID | None = None) -> None:
        with advisory_lock() as acquired:
            if not acquired:
                if run_id is None:
                    self._record_skipped(trigger)
                return
            self._execute(trigger, run_id)

    def _record_skipped(self, trigger: str) -> None:
        now = utcnow()
        with session_scope() as db:
            db.add(ScanRun(
                trigger=trigger, status=ScanStatus.SKIPPED, started_at=now, finished_at=now, duration_ms=0,
                details={"log": [{"ts": now.isoformat(), "level": "warning", "source": None,
                                  "message": "Previous scan still running; this run was skipped to prevent overlap."}]},
            ))

    # ---- execution ------------------------------------------------------------------------
    def _execute(self, trigger: str, run_id: uuid.UUID | None) -> None:
        t0 = time.monotonic()
        log, stats = RunLog(), RunStats()
        with session_scope() as db:
            if run_id is not None:
                run = db.get(ScanRun, run_id)
                if run is None or run.status != ScanStatus.QUEUED:
                    return
            else:
                run = ScanRun(id=uuid.uuid4(), trigger=trigger)
                db.add(run)
            run.status = ScanStatus.RUNNING
            run.started_at = utcnow()
            db.flush()
            run_id = run.id
            source_filter = run.source_id
            sequence = int(get_value(db, "scan_sequence", 0) or 0) + 1
            set_value(db, "scan_sequence", sequence)
            config = get_app_config(db)
            query = select(DiscoverySource).where(DiscoverySource.enabled.is_(True))
            if source_filter:
                query = select(DiscoverySource).where(DiscoverySource.id == source_filter)
            sources = [(s.id, s.connector_key) for s in db.scalars(query.order_by(DiscoverySource.name)).all()]
            write_heartbeat(db, state="running", current_run_id=run_id, run_started_at=run.started_at)
        include_monitored = source_filter is None or any(key == PAGE_CONNECTOR for _, key in sources)

        status = ScanStatus.SUCCEEDED
        try:
            for index, (source_id, _) in enumerate(sources):
                if self.stop.is_set():
                    break
                self._progress(run_id, "discovery", index, len(sources))
                self._run_source(source_id, sequence, config, stats, log)
            if include_monitored and not self.stop.is_set():
                self._process_monitored(run_id, sequence, config, stats, log)
            self._expire_offers(stats, log)
            self._queue_notifications(stats, log)
        except Exception as exc:
            logger.exception("Scan %s aborted", run_id)
            log.add("error", f"Scan aborted: {type(exc).__name__}")
            stats.errors += 1
            status = ScanStatus.FAILED

        if status != ScanStatus.FAILED:
            if self.stop.is_set():
                status = ScanStatus.INTERRUPTED
            elif stats.errors and (stats.sources_ok or stats.products_processed):
                status = ScanStatus.PARTIAL
            elif stats.errors:
                status = ScanStatus.FAILED
        self._finish(run_id, status, stats, log, t0)

    def _progress(self, run_id: uuid.UUID, phase: str, done: int, total: int) -> None:
        with session_scope() as db:
            run = db.get(ScanRun, run_id)
            if run:
                run.progress = {"phase": phase, "done": done, "total": total, "updated_at": utcnow().isoformat()}

    def _run_source(self, source_id: uuid.UUID, sequence: int, config: AppConfig, stats: RunStats, log: RunLog) -> None:
        with session_scope() as db:
            source = db.get(DiscoverySource, source_id)
            if source is None:
                return
            name = source.name
            now = utcnow()
            connector = build_connector(source, self.settings, self.http)
            if not connector.supports_discovery:
                return
            if source.backoff_until and source.backoff_until > now:
                log.add("warning", f"Skipped; backing off until {format_ist(source.backoff_until)}.", name)
                stats.sources_skipped += 1
                stats.source_results.append({"source": name, "status": "backoff"})
                return
            ready, reason = connector.is_configured()
            if not ready:
                source.last_error, source.last_error_at = reason, now
                log.add("warning", f"Not configured: {reason}", name)
                stats.sources_skipped += 1
                stats.source_results.append({"source": name, "status": "not_configured", "reason": reason})
                return
            limiter = self._limiter(source.id, source.rate_limit_per_minute)

        ctx = DiscoveryContext(rate_limiter=limiter, stop_event=self.stop, run_sequence=sequence,
                               log=lambda level, msg: log.add(level, msg, name))
        started = time.monotonic()
        try:
            result = connector.discover(ctx)
        except ConnectorError as exc:
            self._source_failure(source_id, exc, log, name)
            stats.errors += 1
            stats.sources_failed += 1
            stats.source_results.append({"source": name, "status": "failed", "error": str(exc)[:300]})
            return
        except Exception as exc:
            logger.exception("Connector %s crashed", name)
            self._source_failure(source_id, ConnectorError(f"Unexpected connector error: {type(exc).__name__}"), log, name)
            stats.errors += 1
            stats.sources_failed += 1
            stats.source_results.append({"source": name, "status": "failed", "error": type(exc).__name__})
            return

        ingested = 0
        with session_scope() as db:
            source = db.get(DiscoverySource, source_id)
            for obs in result.observations:
                if self.stop.is_set():
                    break
                try:
                    with db.begin_nested():
                        outcome = ingest_observation(db, obs, source=source, config=config)
                except Exception as exc:
                    logger.exception("Ingest failed for %s", obs.url)
                    stats.errors += 1
                    log.add("error", f"Failed to ingest observation: {type(exc).__name__}", name)
                    continue
                stats.absorb(outcome)
                ingested += 0 if outcome.skipped_reason else 1
            source.last_success_at = utcnow()
            source.last_error = None
            source.consecutive_failures = 0
            source.backoff_until = None
        stats.sources_ok += 1
        stats.source_results.append({
            "source": name, "status": "ok", "observations": len(result.observations), "ingested": ingested,
            "requests": result.requests_made, "duration_ms": int((time.monotonic() - started) * 1000),
        })
        log.add("info", f"{len(result.observations)} observations, {ingested} ingested, {result.requests_made} requests.", name)

    def _source_failure(self, source_id: uuid.UUID, exc: ConnectorError, log: RunLog, name: str) -> None:
        with session_scope() as db:
            source = db.get(DiscoverySource, source_id)
            if source is None:
                return
            now = utcnow()
            source.consecutive_failures += 1
            minutes = min(2 ** source.consecutive_failures, 360)
            if isinstance(exc, RateLimited) and exc.retry_after_seconds:
                minutes = max(minutes, exc.retry_after_seconds // 60 + 1)
            if isinstance(exc, AccessBlocked):
                minutes = max(minutes, 60)
            source.backoff_until = now + timedelta(minutes=minutes)
            source.last_error = str(exc)[:500]
            source.last_error_at = now
        log.add("error", f"{exc} Backing off {minutes} min.", name)

    def _process_monitored(self, run_id: uuid.UUID, sequence: int, config: AppConfig, stats: RunStats, log: RunLog) -> None:
        now = utcnow()
        with session_scope() as db:
            due = db.execute(
                select(MonitoredProduct.id, Product.id, Product.product_url, MonitoredProduct.frequency_minutes)
                .join(Product, Product.id == MonitoredProduct.product_id)
                .where(
                    MonitoredProduct.enabled.is_(True),
                    Product.archived_at.is_(None),
                    or_(MonitoredProduct.next_due_at.is_(None), MonitoredProduct.next_due_at <= now),
                )
                .order_by(MonitoredProduct.next_due_at.asc().nulls_first())
                .limit(MAX_MONITORED_PER_RUN)
            ).all()
            if not due:
                return
            page_source = db.scalar(select(DiscoverySource).where(DiscoverySource.connector_key == PAGE_CONNECTOR))
            connector = build_connector(page_source, self.settings, self.http) if page_source else None
            ready, reason = connector.is_configured() if connector else (False, "Product page source missing.")
            if page_source is not None and not page_source.enabled:
                ready, reason = False, "Product page source is disabled."
            if page_source is not None and page_source.backoff_until and page_source.backoff_until > now:
                ready, reason = False, f"Product page source backing off until {format_ist(page_source.backoff_until)}."

            if not ready:
                for mon_id, product_id, _, freq in due:
                    product = db.get(Product, product_id)
                    if product and product.access_status != AccessStatus.NOT_PERMITTED:
                        product.access_status = AccessStatus.NOT_PERMITTED
                        product.last_access_error = reason
                    monitored = db.get(MonitoredProduct, mon_id)
                    monitored.next_due_at = now + timedelta(minutes=freq)
                log.add("info", f"{len(due)} monitored products not refreshed automatically: {reason}", "Monitoring")
                stats.source_results.append({"source": "Monitoring", "status": "not_permitted", "due": len(due), "reason": reason})
                return
            page_source_id = page_source.id
            limiter = self._limiter(page_source.id, page_source.rate_limit_per_minute)

        ctx = DiscoveryContext(rate_limiter=limiter, stop_event=self.stop, run_sequence=sequence,
                               log=lambda level, msg: log.add(level, msg, "Monitoring"))
        refreshed = 0
        for index, (mon_id, product_id, url, freq) in enumerate(due):
            if self.stop.is_set():
                break
            if index % 10 == 0:
                self._progress(run_id, "monitoring", index, len(due))
            stop_all = False
            try:
                obs = connector.fetch_product(url, ctx)
            except (AccessNotPermitted, AccessBlocked) as exc:
                self._mark_product(product_id, AccessStatus.BLOCKED if isinstance(exc, AccessBlocked) else AccessStatus.NOT_PERMITTED, str(exc))
                if isinstance(exc, AccessBlocked):
                    self._source_failure(page_source_id, exc, log, "Monitoring")
                    stats.errors += 1
                else:
                    log.add("warning", str(exc), "Monitoring")
                stop_all = True
                obs = None
            except ConnectorError as exc:
                self._mark_product(product_id, AccessStatus.UNAVAILABLE, str(exc), count_failure=True)
                stats.errors += 1
                log.add("warning", f"Product refresh failed: {exc}", "Monitoring")
                obs = None

            with session_scope() as db:
                if obs is not None:
                    source = db.get(DiscoverySource, page_source_id)
                    try:
                        with db.begin_nested():
                            outcome = ingest_observation(db, obs, source=source, config=config)
                        stats.absorb(outcome)
                        refreshed += 1
                    except Exception as exc:
                        logger.exception("Monitored ingest failed for %s", url)
                        stats.errors += 1
                        log.add("error", f"Failed to process monitored product: {type(exc).__name__}", "Monitoring")
                monitored = db.get(MonitoredProduct, mon_id)
                if monitored:
                    monitored.last_processed_at = utcnow()
                    monitored.next_due_at = utcnow() + timedelta(minutes=freq)
            if stop_all:
                log.add("warning", "Stopped product refresh for this run after an access refusal.", "Monitoring")
                break
        log.add("info", f"Refreshed {refreshed} of {len(due)} due monitored products.", "Monitoring")
        stats.source_results.append({"source": "Monitoring", "status": "ok", "due": len(due), "refreshed": refreshed})

    def _mark_product(self, product_id: uuid.UUID, status: str, error: str, count_failure: bool = False) -> None:
        with session_scope() as db:
            product = db.get(Product, product_id)
            if product is None:
                return
            now = utcnow()
            product.access_status = status
            product.last_access_error = error[:500]
            product.last_checked_at = now
            if not count_failure:
                return
            product.consecutive_failures += 1
            if product.consecutive_failures == UNAVAILABLE_AFTER_FAILURES:
                for offer in db.scalars(select(Offer).where(
                    Offer.product_id == product_id,
                    Offer.source_type == SourceType.PRODUCT_PAGE,
                    Offer.status.notin_((OfferStatus.EXPIRED, OfferStatus.REJECTED, OfferStatus.VERIFIED, OfferStatus.SOURCE_UNAVAILABLE)),
                )).all():
                    offer.status = OfferStatus.SOURCE_UNAVAILABLE
                    offer.last_changed_at = now
                    add_snapshot(db, offer, product, "SOURCE_UNAVAILABLE", {"reason": error[:500]}, now)

    def _expire_offers(self, stats: RunStats, log: RunLog) -> None:
        now = utcnow()
        with session_scope() as db:
            offers = db.scalars(
                select(Offer).where(
                    Offer.valid_until.is_not(None),
                    Offer.valid_until < now,
                    Offer.status.notin_((OfferStatus.EXPIRED, OfferStatus.REJECTED)),
                ).limit(1000)
            ).all()
            for offer in offers:
                offer.status = OfferStatus.EXPIRED
                offer.expired_at = now
                offer.last_changed_at = now
                add_snapshot(db, offer, offer.product, "VALIDITY_ENDED", {"valid_until": offer.valid_until.isoformat()}, now)
            stats.offers_expired += len(offers)
        if offers:
            log.add("info", f"Marked {len(offers)} offers expired (validity ended).")

    def _queue_notifications(self, stats: RunStats, log: RunLog) -> None:
        with session_scope() as db:
            queued = queue_offer_events(db, stats.new_offer_ids, stats.changed_offer_ids)
            queued += queue_expiring(db, utcnow())
        stats.notifications_queued += queued
        if queued:
            log.add("info", f"Queued {queued} notifications.")

    def _finish(self, run_id: uuid.UUID, status: str, stats: RunStats, log: RunLog, t0: float) -> None:
        with session_scope() as db:
            run = db.get(ScanRun, run_id)
            if run is None:
                return
            run.status = status
            run.finished_at = utcnow()
            run.duration_ms = int((time.monotonic() - t0) * 1000)
            run.products_discovered = stats.products_discovered
            run.products_processed = stats.products_processed
            run.offers_detected = stats.offers_detected
            run.offers_new = stats.offers_new
            run.offers_expired = stats.offers_expired
            run.notifications_queued = stats.notifications_queued
            run.errors_count = stats.errors
            run.progress = {"phase": "finished", "updated_at": utcnow().isoformat()}
            run.details = {
                "log": log.entries,
                "sources": stats.source_results,
                "summary": {"sources_ok": stats.sources_ok, "sources_failed": stats.sources_failed, "sources_skipped": stats.sources_skipped},
            }
            write_heartbeat(db, state="idle", current_run_id=None, last_run_id=run_id, last_run_status=status, last_run_finished_at=run.finished_at)
        logger.info("Scan %s finished: %s in %d ms", run_id, status, int((time.monotonic() - t0) * 1000))

    # ---- maintenance ----------------------------------------------------------------------
    def retention_cleanup(self) -> None:
        with session_scope() as db:
            config = get_app_config(db)
            now = utcnow()
            db.execute(delete(ScanRun).where(
                ScanRun.queued_at < now - timedelta(days=config.retention_days_scan_runs),
                ScanRun.status.notin_((ScanStatus.RUNNING, ScanStatus.QUEUED)),
            ))
            db.execute(delete(Notification).where(
                Notification.created_at < now - timedelta(days=config.retention_days_notifications),
                Notification.status.in_((NotificationStatus.SENT, NotificationStatus.DRY_RUN, NotificationStatus.SUPPRESSED, NotificationStatus.FAILED)),
            ))
