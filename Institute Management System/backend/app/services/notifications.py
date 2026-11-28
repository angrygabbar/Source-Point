import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.integrations import registry
from app.models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
    Parent,
    StudentParent,
    Student,
    User,
    UserRole,
    Role,
)
from app.services import feature_flags
from app.services.audit import jsonable

EXTERNAL_CHANNELS = ("email", "sms", "whatsapp", "push")


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render(template: str, context: dict[str, Any]) -> str:
    return template.format_map(_SafeDict({k: ("" if v is None else v) for k, v in context.items()}))


def active_channels(db: Session, institute_id: uuid.UUID | None) -> set[str]:
    flags = feature_flags.get_flags(db, institute_id)
    out: set[str] = set()
    for ch in EXTERNAL_CHANNELS:
        if flags.get(ch) and registry.get_active(db, institute_id, ch) is not None:
            out.add(ch)
    return out


def notify(
    db: Session,
    institute_id: uuid.UUID | None,
    user_ids: Iterable[uuid.UUID | None],
    event_type: str,
    title: str,
    body: str = "",
    link: str | None = None,
    data: dict | None = None,
    dedupe_key: str | None = None,
    context: dict[str, Any] | None = None,
) -> int:
    """Create in-app notifications and queue external deliveries for configured channels only."""
    ids = {u for u in user_ids if u}
    if not ids:
        return 0
    channels = active_channels(db, institute_id)
    templates = {}
    if channels:
        for t in db.scalars(
            select(NotificationTemplate).where(
                NotificationTemplate.event_type == event_type,
                NotificationTemplate.is_active.is_(True),
                (NotificationTemplate.institute_id == institute_id) | NotificationTemplate.institute_id.is_(None),
            )
        ):
            if t.channel not in templates or t.institute_id is not None:
                templates[t.channel] = t
    prefs = {
        (p.user_id, p.channel): p.enabled
        for p in db.scalars(
            select(NotificationPreference).where(
                NotificationPreference.user_id.in_(ids), NotificationPreference.event_type == event_type
            )
        )
    }
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(ids), User.is_active.is_(True)))}
    created = 0
    now = datetime.now(timezone.utc)
    ctx = {"title": title, "body": body, "link": link or "", **(context or {})}
    for uid, user in users.items():
        if prefs.get((uid, "in_app"), True) is False and not channels:
            continue
        stmt = (
            insert(Notification)
            .values(
                id=uuid.uuid4(),
                institute_id=institute_id,
                user_id=uid,
                event_type=event_type,
                title=title[:255],
                body=body,
                link=link,
                data=jsonable(data or {}),
                is_read=False,
                dedupe_key=dedupe_key,
            )
            .returning(Notification.id)
        )
        if dedupe_key:
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["user_id", "dedupe_key"], index_where=Notification.dedupe_key.isnot(None)
            )
        notif_id = db.scalar(stmt)
        if notif_id is None:
            continue  # duplicate suppressed
        created += 1
        for ch in channels:
            if prefs.get((uid, ch), True) is False:
                continue
            recipient = user.email if ch == "email" else (str(uid) if ch == "push" else user.phone)
            if not recipient:
                continue
            tpl = templates.get(ch)
            subject = render(tpl.subject, {**ctx, "name": user.full_name}) if tpl and tpl.subject else title
            text = render(tpl.body, {**ctx, "name": user.full_name}) if tpl else f"{title}\n\n{body}".strip()
            db.add(
                NotificationDelivery(
                    institute_id=institute_id,
                    notification_id=notif_id,
                    user_id=uid,
                    channel=ch,
                    recipient=recipient,
                    subject=subject[:255],
                    body=text,
                    status="queued",
                    scheduled_at=now,
                    next_attempt_at=now,
                    dedupe_key=f"{dedupe_key}:{ch}:{uid}" if dedupe_key else None,
                )
            )
    return created


def staff_user_ids(db: Session, institute_id: uuid.UUID, role_codes: tuple[str, ...] = ("institute_admin", "branch_admin")) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .join(User, User.id == UserRole.user_id)
            .where(Role.code.in_(role_codes), User.institute_id == institute_id, User.is_active.is_(True))
        ).all()
    )


def student_and_parent_user_ids(db: Session, student_ids: Iterable[uuid.UUID], include_student: bool = True) -> list[uuid.UUID]:
    sids = list(set(student_ids))
    if not sids:
        return []
    out: list[uuid.UUID] = []
    if include_student:
        out += [u for u in db.scalars(select(Student.user_id).where(Student.id.in_(sids))).all() if u]
    out += [
        u
        for u in db.scalars(
            select(Parent.user_id).join(StudentParent, StudentParent.parent_id == Parent.id).where(StudentParent.student_id.in_(sids))
        ).all()
        if u
    ]
    return out
