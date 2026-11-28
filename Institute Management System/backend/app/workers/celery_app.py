from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

celery_app = Celery("classflow", broker=settings.REDIS_URL, backend=settings.REDIS_URL, include=["app.workers.tasks"])
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.DEFAULT_TIMEZONE,
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_hijack_root_logger=False,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "dispatch-outbox": {"task": "app.workers.tasks.dispatch_outbox", "schedule": 15.0},
        "send-deliveries": {"task": "app.workers.tasks.send_deliveries", "schedule": 30.0},
        "webhook-deliveries": {"task": "app.workers.tasks.send_webhooks", "schedule": 60.0},
        "finalise-exams": {"task": "app.workers.tasks.finalise_exam_attempts", "schedule": 60.0},
        "follow-up-reminders": {"task": "app.workers.tasks.follow_up_reminders", "schedule": crontab(minute="*/15")},
        "generate-sessions": {"task": "app.workers.tasks.generate_upcoming_sessions", "schedule": crontab(hour=0, minute=30)},
        "daily-finance": {"task": "app.workers.tasks.daily_finance", "schedule": crontab(hour=1, minute=0)},
        "daily-academic-alerts": {"task": "app.workers.tasks.daily_academic_alerts", "schedule": crontab(hour=7, minute=0)},
        "homework-reminders": {"task": "app.workers.tasks.homework_reminders", "schedule": crontab(minute=0)},
        "library-reminders": {"task": "app.workers.tasks.library_reminders", "schedule": crontab(hour=8, minute=0)},
        "usage-and-retention": {"task": "app.workers.tasks.usage_and_retention", "schedule": crontab(hour=3, minute=0)},
    },
)
