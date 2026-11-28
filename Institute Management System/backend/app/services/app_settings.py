import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApplicationSetting

APP_SETTING_DEFAULTS: dict[str, Any] = {
    "attendance.alert_threshold_percent": 75,
    "attendance.lock_on_submit": True,
    "billing.billable_attendance_statuses": ["present", "late"],
    "billing.auto_generate_invoices": False,
    "billing.invoice_lead_days": 0,
    "communication.students_can_message_teachers": True,
    "communication.parents_can_message_teachers": True,
    "communication.students_can_message_students": False,
    "communication.show_teacher_contact_to_parents": False,
    "homework.reminder_hours_before_due": 24,
    "admissions.follow_up_reminder_minutes": 60,
    "syllabus.delay_alert_days": 7,
    "evaluation.pending_alert_days": 3,
    "retention.login_history_days": 365,
    "retention.notification_days": 180,
    "retention.audit_log_days": 0,
    "ai.monthly_request_limit": 500,
    "ai.allow_student_data": False,
    "storage.quota_warning_percent": 85,
}


def get_all(db: Session, institute_id: uuid.UUID) -> dict[str, Any]:
    out = dict(APP_SETTING_DEFAULTS)
    for row in db.scalars(select(ApplicationSetting).where(ApplicationSetting.institute_id == institute_id)):
        if row.key in out:
            out[row.key] = (row.value or {}).get("v", out[row.key])
    return out


def get(db: Session, institute_id: uuid.UUID, key: str) -> Any:
    row = db.scalar(select(ApplicationSetting).where(ApplicationSetting.institute_id == institute_id, ApplicationSetting.key == key))
    if row is not None:
        return (row.value or {}).get("v", APP_SETTING_DEFAULTS.get(key))
    return APP_SETTING_DEFAULTS.get(key)


def put(db: Session, institute_id: uuid.UUID, key: str, value: Any) -> None:
    if key not in APP_SETTING_DEFAULTS:
        raise ValueError(f"Unknown setting '{key}'")
    default = APP_SETTING_DEFAULTS[key]
    if isinstance(default, bool):
        value = bool(value)
    elif isinstance(default, int):
        value = int(value)
    elif isinstance(default, list) and not isinstance(value, list):
        raise ValueError(f"Setting '{key}' must be a list")
    row = db.scalar(select(ApplicationSetting).where(ApplicationSetting.institute_id == institute_id, ApplicationSetting.key == key))
    if row is None:
        row = ApplicationSetting(institute_id=institute_id, key=key)
        db.add(row)
    row.value = {"v": value}
