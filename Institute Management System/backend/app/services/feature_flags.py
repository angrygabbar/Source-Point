import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import FeatureFlag

# key -> (default enabled, description). Core security/audit cannot be disabled and is not listed.
DEFAULT_FLAGS: dict[str, tuple[bool, str]] = {
    "attendance": (True, "Student & teacher attendance"),
    "homework": (True, "Homework and assignments"),
    "materials": (True, "Study materials"),
    "billing": (True, "Fees, invoices and payments"),
    "teacher_compensation": (True, "Teacher compensation"),
    "examinations": (True, "Examinations and question bank"),
    "lms": (True, "LMS and online learning"),
    "admissions": (True, "Admissions CRM"),
    "hr_payroll": (True, "HR and payroll"),
    "parent_portal": (True, "Parent portal"),
    "library": (False, "Library"),
    "inventory": (False, "Inventory and assets"),
    "multi_branch": (True, "Multiple branches"),
    "saas": (False, "SaaS subscription management"),
    "accounting": (True, "Expenses and accounting"),
    "communication": (True, "Announcements and messaging"),
    "email": (False, "Email notifications (requires provider)"),
    "sms": (False, "SMS notifications (requires provider)"),
    "whatsapp": (False, "WhatsApp notifications (requires provider)"),
    "push": (False, "Push notifications (requires VAPID keys)"),
    "online_payments": (False, "Online payment gateway (requires provider)"),
    "ai": (False, "AI services (requires provider)"),
    "video_meetings": (False, "Video meeting integrations (requires provider)"),
}


def get_flags(db: Session, institute_id: uuid.UUID | None) -> dict[str, bool]:
    flags = {k: v[0] for k, v in DEFAULT_FLAGS.items()}
    rows = db.scalars(
        select(FeatureFlag).where(or_(FeatureFlag.institute_id.is_(None), FeatureFlag.institute_id == institute_id))
    ).all()
    # Platform defaults first, then institute overrides.
    for row in sorted(rows, key=lambda r: r.institute_id is not None):
        if row.key in flags:
            flags[row.key] = bool(row.enabled)
    return flags


def is_enabled(db: Session, institute_id: uuid.UUID | None, key: str) -> bool:
    if key not in DEFAULT_FLAGS:
        return True
    return get_flags(db, institute_id).get(key, True)


def set_flag(db: Session, institute_id: uuid.UUID, key: str, enabled: bool) -> None:
    if key not in DEFAULT_FLAGS:
        raise ValueError(f"Unknown feature flag '{key}'")
    row = db.scalar(select(FeatureFlag).where(FeatureFlag.institute_id == institute_id, FeatureFlag.key == key))
    if row is None:
        row = FeatureFlag(institute_id=institute_id, key=key, description=DEFAULT_FLAGS[key][1])
        db.add(row)
    row.enabled = enabled
