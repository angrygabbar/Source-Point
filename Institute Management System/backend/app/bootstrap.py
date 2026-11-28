"""Idempotent system bootstrap: permissions, system roles, defaults and institute provisioning."""

import uuid
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.permissions import DEFAULT_ROLES, all_permission_codes
from app.core.security import generate_temp_password, hash_password, validate_password_strength
from app.models import (
    AcademicYear,
    Branch,
    ExpenseCategory,
    FeatureFlag,
    GradeScale,
    Institute,
    NotificationTemplate,
    Permission,
    Role,
    RolePermission,
    SubscriptionPlan,
    User,
    UserRole,
)
from app.integrations import registry

DEFAULT_TEMPLATES = [
    ("student_absence", "email", "Absence: {student_name}", "Dear {name},\n\n{student_name} was marked {status} for {subject} on {date}.\n\n— {institute}"),
    ("teacher_absence", "email", "Teacher absence notice", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("fee_due", "email", "Fee due: {invoice_number}", "Dear {name},\n\nInvoice {invoice_number} for {amount} is due on {due_date}.\n\n— {institute}"),
    ("fee_overdue", "email", "Overdue: {invoice_number}", "Dear {name},\n\nInvoice {invoice_number} ({amount}) is overdue since {due_date}. Please clear the balance.\n\n— {institute}"),
    ("payment_received", "email", "Payment received {receipt_number}", "Dear {name},\n\nWe received {amount} (receipt {receipt_number}). Thank you.\n\n— {institute}"),
    ("class_cancelled", "email", "Class cancelled", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("class_rescheduled", "email", "Class rescheduled", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("material_uploaded", "email", "New study material: {title}", "Dear {name},\n\nNew study material is available: {body}\n\n— {institute}"),
    ("assignment_published", "email", "New homework: {title}", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("homework_deadline", "email", "Homework due soon: {title}", "Dear {name},\n\n{body}\n\nPlease submit your work before the deadline.\n\n— {institute}"),
    ("submission_received", "email", "Submission received: {title}", "Dear {name},\n\nA learner submitted work for {title}. {body}\n\n— {institute}"),
    ("submission_evaluated", "email", "Homework evaluated: {title}", "Dear {name},\n\nYour homework has been evaluated. {body}\n\n— {institute}"),
    ("admission", "email", "Admission update: {title}", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("announcement", "email", "{title}", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("leave_decision", "email", "Leave request update", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("follow_up_due", "email", "Admission follow-up due", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("evaluation_pending", "email", "Evaluations pending: {title}", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("syllabus_delay", "email", "Syllabus progress needs attention", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("attendance_alert", "email", "Attendance alert", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("message", "email", "{title}", "Dear {name},\n\n{body}\n\n— {institute}"),
    ("exam_results", "email", "Exam results: {title}", "Dear {name},\n\nYour exam results have been published. {body}\n\n— {institute}"),
    ("system", "email", "Institute Management System update: {title}", "Dear {name},\n\n{body}\n\n— {institute}"),
]

DEFAULT_EXPENSE_CATEGORIES = [
    ("RENT", "Rent"), ("UTIL", "Utilities"), ("SAL", "Salaries"), ("MKT", "Marketing"), ("STAT", "Stationery"),
    ("MAINT", "Maintenance"), ("TECH", "Software & IT"), ("MISC", "Miscellaneous"),
]

DEFAULT_GRADE_BANDS = [
    {"min": 90, "max": 100, "grade": "A+", "point": 10}, {"min": 80, "max": 89.99, "grade": "A", "point": 9},
    {"min": 70, "max": 79.99, "grade": "B+", "point": 8}, {"min": 60, "max": 69.99, "grade": "B", "point": 7},
    {"min": 50, "max": 59.99, "grade": "C", "point": 6}, {"min": 40, "max": 49.99, "grade": "D", "point": 5},
    {"min": 0, "max": 39.99, "grade": "E", "point": 0},
]


def seed_system(db: Session) -> dict:
    existing = {p.code: p for p in db.scalars(select(Permission))}
    for code, module, desc, sensitive in all_permission_codes():
        if code not in existing:
            perm = Permission(code=code, module=module, description=desc, is_sensitive=sensitive)
            db.add(perm)
            existing[code] = perm
        else:
            existing[code].description = desc
            existing[code].is_sensitive = sensitive
    db.flush()
    for code, spec in DEFAULT_ROLES.items():
        role = db.scalar(select(Role).where(Role.code == code, Role.institute_id.is_(None)))
        if role is None:
            role = Role(code=code, name=spec["name"], portal=spec["portal"], is_system=True, institute_id=None)
            db.add(role)
            db.flush()
        role.name = spec["name"]
        role.portal = spec["portal"]
        db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        for pcode in sorted(spec["permissions"]):
            if pcode in existing:
                db.add(RolePermission(role_id=role.id, permission_id=existing[pcode].id))
    if not db.scalar(select(func.count()).select_from(SubscriptionPlan)):
        db.add(SubscriptionPlan(code="self_hosted", name="Self-hosted", description="Single self-hosted institute (no billing)",
                                price_monthly=0, price_annual=0, modules=[], trial_days=0))
    db.flush()
    added_templates = 0
    enabled_email_flags = 0
    for inst in db.scalars(select(Institute).where(Institute.is_active.is_(True))):
        added_templates += seed_notification_templates(db, inst.id)
        # Default email notifications on only when a provider is configured. An
        # existing per-institute flag remains authoritative so admins can opt out.
        email_flag = db.scalar(
            select(FeatureFlag).where(FeatureFlag.institute_id == inst.id, FeatureFlag.key == "email")
        )
        if email_flag is None and registry.get_active(db, inst.id, "email") is not None:
            db.add(FeatureFlag(institute_id=inst.id, key="email", enabled=True,
                               description="Email notifications (requires provider)"))
            enabled_email_flags += 1
    db.flush()
    return {
        "permissions": len(existing),
        "roles": len(DEFAULT_ROLES),
        "notification_templates": added_templates,
        "email_flags": enabled_email_flags,
    }


def seed_notification_templates(db: Session, institute_id) -> int:
    existing = {
        (row.event_type, row.channel)
        for row in db.scalars(
            select(NotificationTemplate).where(NotificationTemplate.institute_id == institute_id)
        )
    }
    added = 0
    for event, channel, subject, body in DEFAULT_TEMPLATES:
        if (event, channel) in existing:
            continue
        db.add(NotificationTemplate(institute_id=institute_id, event_type=event, channel=channel,
                                    subject=subject, body=body))
        added += 1
    db.flush()
    return added


def _fy_bounds(today: date, start_month: int = 4) -> tuple[date, date, str]:
    y = today.year if today.month >= start_month else today.year - 1
    return date(y, start_month, 1), date(y + 1, start_month, 1) - timedelta(days=1), f"{y}-{str(y + 1)[-2:]}"


def provision_institute(
    db: Session,
    name: str,
    code: str,
    admin_email: str,
    admin_name: str,
    admin_password: str | None,
    branch_name: str = "Main Branch",
) -> tuple[Institute, User, str | None]:
    seed_system(db)
    if db.scalar(select(Institute.id).where(Institute.code == code)):
        raise ValueError(f"Institute code '{code}' already exists")
    if db.scalar(select(User.id).where(func.lower(User.email) == admin_email.lower())):
        raise ValueError("Admin email already exists")
    inst = Institute(name=name, code=code)
    db.add(inst)
    db.flush()
    branch = Branch(institute_id=inst.id, name=branch_name, code="MAIN", is_head_office=True)
    db.add(branch)
    start, end, label = _fy_bounds(date.today())
    db.add(AcademicYear(institute_id=inst.id, name=label, start_date=start, end_date=end, status="active", is_current=True))
    for c, n in DEFAULT_EXPENSE_CATEGORIES:
        db.add(ExpenseCategory(institute_id=inst.id, code=c, name=n))
    db.add(GradeScale(institute_id=inst.id, name="Default percentage scale", bands=DEFAULT_GRADE_BANDS, is_default=True))
    seed_notification_templates(db, inst.id)
    temp = None
    if admin_password:
        validate_password_strength(admin_password)
    else:
        temp = generate_temp_password()
        admin_password = temp
    admin = User(institute_id=inst.id, email=admin_email.lower(), full_name=admin_name, password_hash=hash_password(admin_password),
                 is_active=True, must_change_password=temp is not None, default_branch_id=None)
    db.add(admin)
    db.flush()
    role = db.scalar(select(Role).where(Role.code == "institute_admin", Role.institute_id.is_(None)))
    db.add(UserRole(user_id=admin.id, role_id=role.id, branch_id=None))
    db.flush()
    return inst, admin, temp


def create_superuser(db: Session, email: str, full_name: str, password: str | None) -> tuple[User, str | None]:
    seed_system(db)
    if db.scalar(select(User.id).where(func.lower(User.email) == email.lower())):
        raise ValueError("User already exists")
    temp = None
    if password:
        validate_password_strength(password)
    else:
        temp = generate_temp_password()
        password = temp
    u = User(institute_id=None, email=email.lower(), full_name=full_name, password_hash=hash_password(password),
             is_superuser=True, is_active=True, must_change_password=temp is not None)
    db.add(u)
    db.flush()
    return u, temp


def new_id() -> uuid.UUID:
    return uuid.uuid4()
