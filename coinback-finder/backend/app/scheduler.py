"""Scanner process entry point: `python -m app.scheduler`."""

from __future__ import annotations

import logging
import os
import signal
import threading
from collections.abc import Callable
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.database.enums import ScanTrigger
from app.database.session import SessionLocal, session_scope
from app.notifications.bot import poll_commands
from app.notifications.service import dispatch_pending
from app.notifications.telegram import TelegramClient
from app.scanner.runner import ScanRunner
from app.services.bootstrap import ensure_defaults
from app.services.clock import IST, utcnow
from app.services.settings_store import get_app_config, set_value

logger = logging.getLogger("coinback.scanner")


def _safe(name: str, fn: Callable[[], object]) -> Callable[[], None]:
    def wrapper() -> None:
        try:
            fn()
        except Exception:
            logger.exception("Job %s failed", name)
    return wrapper


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stop = threading.Event()

    with SessionLocal() as db:
        ensure_defaults(db)
        interval = get_app_config(db).scan_interval_minutes

    runner = ScanRunner(settings, stop)
    runner.recover_interrupted()
    telegram = TelegramClient(settings.telegram_bot_token, dry_run=settings.telegram_dry_run)
    current_interval = {"minutes": interval}

    scheduler = BackgroundScheduler(
        timezone=IST,
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
    )

    def scheduled_scan() -> None:
        if settings.scanner_enabled:
            runner.run_cycle(ScanTrigger.SCHEDULED)

    def dispatch() -> None:
        with SessionLocal() as db:
            dispatch_pending(db, telegram, settings)

    def commands() -> None:
        with SessionLocal() as db:
            poll_commands(db, telegram, settings)

    def sync_interval() -> None:
        with SessionLocal() as db:
            wanted = get_app_config(db).scan_interval_minutes
        if wanted != current_interval["minutes"]:
            scheduler.reschedule_job("scan", trigger=IntervalTrigger(minutes=wanted, timezone=IST))
            current_interval["minutes"] = wanted
            logger.info("Scan interval changed to %d minutes", wanted)

    scheduler.add_job(_safe("scan", scheduled_scan), IntervalTrigger(minutes=interval, timezone=IST), id="scan",
                      next_run_time=utcnow() + timedelta(seconds=30))
    scheduler.add_job(_safe("manual", runner.run_queued), IntervalTrigger(seconds=15), id="manual")
    scheduler.add_job(_safe("dispatch", dispatch), IntervalTrigger(seconds=30), id="dispatch")
    scheduler.add_job(_safe("sync_interval", sync_interval), IntervalTrigger(seconds=60), id="sync_interval")
    scheduler.add_job(_safe("retention", runner.retention_cleanup), CronTrigger(hour=3, minute=30, timezone=IST), id="retention")
    if settings.telegram_commands_enabled and not telegram.dry_run:
        scheduler.add_job(_safe("telegram_commands", commands), IntervalTrigger(seconds=5), id="telegram_commands")

    def _shutdown(signum: int, _frame: object) -> None:
        logger.info("Signal %s received; shutting down after current step", signum)
        stop.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    scheduler.start()
    logger.info("Scanner started (interval %d min, telegram %s)", interval, "dry-run" if telegram.dry_run else "live")
    while not stop.wait(15):
        job = scheduler.get_job("scan")
        try:
            with session_scope() as db:
                set_value(db, "scanner_schedule", {
                    "alive_at": utcnow().isoformat(),
                    "next_scan_at": job.next_run_time.isoformat() if job and job.next_run_time else None,
                    "interval_minutes": current_interval["minutes"],
                    "scanner_enabled": settings.scanner_enabled,
                    "telegram_mode": "dry-run" if telegram.dry_run else "live",
                    "pid": os.getpid(),
                })
        except Exception:
            logger.exception("Failed to write scanner schedule heartbeat")

    scheduler.shutdown(wait=True)
    runner.close()
    telegram.close()
    logger.info("Scanner stopped")


if __name__ == "__main__":
    main()
