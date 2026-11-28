import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.api.common import get_tenant_obj
from app.api.deps import Principal, get_principal, require_feature, require_perm
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.core.security import sha256_hex
from app.crud.engine import REGISTRY, base_query, read_mode
from app.db.session import get_db
from app.integrations import registry
from app.models import (
    Announcement,
    AnnouncementAcknowledgement,
    Message,
    MessageThread,
    MessageThreadParticipant,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    Parent,
    PushSubscription,
    Role,
    Student,
    StudentEnrollment,
    StudentParent,
    Survey,
    SurveyResponse,
    Teacher,
    TeacherAssignment,
    User,
    UserRole,
)
from app.models.communication import CHANNELS, NOTIFICATION_EVENTS
from app.services import app_settings, audit, outbox

router = APIRouter(tags=["Communication"])


# ----------------------------------------------------------------------------- announcements


@router.post("/announcements/{aid}/publish", dependencies=[Depends(require_feature("communication"))])
def publish_announcement(aid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    a = get_tenant_obj(db, p, Announcement, aid, lock=True, label="Announcement")
    if not (p.can("announcements.write") or (p.can("announcements.write_own") and a.created_by_id == p.user_id
                                              and a.audience == "batch" and a.batch_id in p.batch_ids)):
        raise Forbidden("You cannot publish this announcement (teachers publish to their own batches)")
    if a.status != "draft":
        raise Conflict("Only drafts can be published")
    if a.audience == "batch" and not a.batch_id:
        raise ValidationFailed("Select a batch for batch announcements")
    a.status = "published"
    a.published_at = datetime.now(timezone.utc)
    audit.record(db, p, "announcements", a.id, "publish", branch_id=a.branch_id)
    outbox.emit(db, p.institute_id, "announcement.published", "announcement", a.id, {"title": a.title}, dedupe_key=f"announcement:{a.id}")
    db.commit()
    return {"status": a.status}


@router.post("/announcements/{aid}/archive", dependencies=[Depends(require_feature("communication"))])
def archive_announcement(aid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    a = get_tenant_obj(db, p, Announcement, aid, lock=True, label="Announcement")
    if not (p.can("announcements.write") or a.created_by_id == p.user_id):
        raise Forbidden("You cannot archive this announcement")
    a.status = "archived"
    audit.record(db, p, "announcements", a.id, "archive")
    db.commit()
    return {"status": a.status}


@router.post("/announcements/{aid}/acknowledge", dependencies=[Depends(require_feature("communication"))])
def acknowledge(aid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    res = REGISTRY["announcements"]
    mode = read_mode(p, res)
    if mode is None or db.scalar(base_query(p, res, mode).where(Announcement.id == aid)) is None:
        raise NotFound("Announcement not found")
    db.execute(insert(AnnouncementAcknowledgement).values(id=uuid.uuid4(), institute_id=p.institute_id, announcement_id=aid, user_id=p.user_id)
               .on_conflict_do_nothing(index_elements=["announcement_id", "user_id"]))
    db.commit()
    return {"ok": True}


@router.get("/announcements/{aid}/acknowledgements", dependencies=[Depends(require_feature("communication"))])
def acknowledgements(aid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    a = get_tenant_obj(db, p, Announcement, aid, label="Announcement")
    if not (p.can("announcements.read") or a.created_by_id == p.user_id):
        raise Forbidden("Only staff can view acknowledgements")
    rows = db.execute(select(User.full_name, AnnouncementAcknowledgement.created_at).join(User, User.id == AnnouncementAcknowledgement.user_id)
                      .where(AnnouncementAcknowledgement.announcement_id == a.id).order_by(AnnouncementAcknowledgement.created_at)).all()
    return {"count": len(rows), "items": [{"name": n, "at": t} for n, t in rows]}


@router.get("/announcements/feed/mine")
def my_announcements(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    res = REGISTRY["announcements"]
    mode = read_mode(p, res)
    if mode is None:
        return []
    rows = db.scalars(base_query(p, res, mode).where(Announcement.status == "published").order_by(Announcement.published_at.desc()).limit(30)).all()
    acked = set(db.scalars(select(AnnouncementAcknowledgement.announcement_id).where(AnnouncementAcknowledgement.user_id == p.user_id)))
    return [{"id": a.id, "title": a.title, "body": a.body, "priority": a.priority, "published_at": a.published_at,
             "requires_acknowledgement": a.requires_acknowledgement, "acknowledged": a.id in acked} for a in rows]


# ----------------------------------------------------------------------------- messaging with boundaries


def _role_codes(db: Session, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, set[str]]:
    out: dict[uuid.UUID, set[str]] = {}
    for uid, code, portal in db.execute(select(UserRole.user_id, Role.code, Role.portal).join(Role, Role.id == UserRole.role_id)
                                        .where(UserRole.user_id.in_(user_ids))).all():
        out.setdefault(uid, set()).update({code, f"portal:{portal}"})
    return out


def allowed_contacts(db: Session, p: Principal) -> set[uuid.UUID]:
    """User ids the principal may message, enforcing configurable communication boundaries."""
    inst = p.institute_id
    staff_ids = set(db.scalars(select(UserRole.user_id).join(Role, Role.id == UserRole.role_id).join(User, User.id == UserRole.user_id)
                               .where(Role.portal == "admin", User.institute_id == inst, User.is_active.is_(True))))
    if p.is_staff:
        return set(db.scalars(select(User.id).where(User.institute_id == inst, User.is_active.is_(True)))) - {p.user_id}
    allowed = set(staff_ids)
    s = app_settings.get_all(db, inst)
    if p.teacher_id:
        enrolled = select(StudentEnrollment.student_id).where(StudentEnrollment.batch_id.in_(p.batch_ids or [uuid.uuid4()]),
                                                              StudentEnrollment.status == "active")
        allowed |= {u for u in db.scalars(select(Student.user_id).where(Student.id.in_(enrolled))) if u}
        allowed |= {u for u in db.scalars(select(Parent.user_id).join(StudentParent, StudentParent.parent_id == Parent.id)
                                          .where(StudentParent.student_id.in_(enrolled))) if u}
        allowed |= {u for u in db.scalars(select(Teacher.user_id).where(Teacher.institute_id == inst)) if u}
    if p.linked_student_ids:
        teacher_ids = select(TeacherAssignment.teacher_id).where(TeacherAssignment.batch_id.in_(p.batch_ids or [uuid.uuid4()]),
                                                                 TeacherAssignment.is_active.is_(True))
        teachers = {u for u in db.scalars(select(Teacher.user_id).where(Teacher.id.in_(teacher_ids))) if u}
        if p.student_id and s["communication.students_can_message_teachers"]:
            allowed |= teachers
        if p.parent_id and s["communication.parents_can_message_teachers"]:
            allowed |= teachers
        if p.student_id and s["communication.students_can_message_students"]:
            peers = select(StudentEnrollment.student_id).where(StudentEnrollment.batch_id.in_(p.batch_ids or [uuid.uuid4()]),
                                                               StudentEnrollment.status == "active")
            allowed |= {u for u in db.scalars(select(Student.user_id).where(Student.id.in_(peers))) if u}
    allowed.discard(p.user_id)
    return allowed


@router.get("/messages/contacts")
def contacts(q: str | None = Query(None, max_length=100), db: Session = Depends(get_db), p: Principal = Depends(require_feature("communication"))):
    ids = allowed_contacts(db, p)
    if not ids:
        return []
    query = select(User.id, User.full_name).where(User.id.in_(ids))
    if q:
        query = query.where(User.full_name.ilike(f"%{q}%"))
    rows = db.execute(query.order_by(User.full_name).limit(50)).all()
    roles = _role_codes(db, {r[0] for r in rows})
    # Contact details (phone/email) are intentionally never exposed here.
    return [{"user_id": uid, "name": n, "roles": sorted(c for c in roles.get(uid, set()) if not c.startswith("portal:"))} for uid, n in rows]


class ThreadIn(BaseModel):
    subject: str = Field(min_length=2, max_length=255)
    participant_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)
    body: str = Field(min_length=1, max_length=10000)
    related_student_id: uuid.UUID | None = None


@router.post("/messages/threads", status_code=201)
def create_thread(body: ThreadIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("communication"))):
    if not (p.can("messages.write") or p.can("messages.write_own")):
        raise Forbidden("Messaging is not available for your role")
    allowed = allowed_contacts(db, p)
    bad = set(body.participant_ids) - allowed
    if bad:
        raise Forbidden("You are not permitted to message one or more selected recipients")
    if body.related_student_id and not (p.is_staff or p.teacher_id or body.related_student_id in p.linked_student_ids):
        raise Forbidden("Invalid related student")
    now = datetime.now(timezone.utc)
    kind = "parent_teacher" if p.parent_id or body.related_student_id else ("group" if len(body.participant_ids) > 1 else "direct")
    t = MessageThread(institute_id=p.institute_id, subject=body.subject, thread_type=kind, created_by_id=p.user_id,
                      related_student_id=body.related_student_id, last_message_at=now)
    db.add(t)
    db.flush()
    for uid in set(body.participant_ids) | {p.user_id}:
        db.add(MessageThreadParticipant(institute_id=p.institute_id, thread_id=t.id, user_id=uid, last_read_at=now if uid == p.user_id else None))
    db.add(Message(institute_id=p.institute_id, thread_id=t.id, sender_id=p.user_id, body=body.body))
    outbox.emit(db, p.institute_id, "message.sent", "message_thread", t.id, {"sender": p.user.full_name if p.user else "", "subject": body.subject})
    db.commit()
    return {"id": t.id}


def _participant(db: Session, p: Principal, tid: uuid.UUID, lock: bool = False) -> tuple[MessageThread, MessageThreadParticipant | None]:
    t = get_tenant_obj(db, p, MessageThread, tid, label="Conversation")
    part = db.scalar(select(MessageThreadParticipant).where(MessageThreadParticipant.thread_id == t.id, MessageThreadParticipant.user_id == p.user_id))
    if part is None and not p.can("messages.write"):
        raise NotFound("Conversation not found")
    return t, part


@router.get("/messages/threads")
def my_threads(page: int = Query(1, ge=1), db: Session = Depends(get_db), p: Principal = Depends(require_feature("communication"))):
    sub = select(MessageThreadParticipant.thread_id).where(MessageThreadParticipant.user_id == p.user_id)
    threads = db.scalars(select(MessageThread).where(MessageThread.id.in_(sub)).order_by(MessageThread.last_message_at.desc().nullslast())
                         .offset((page - 1) * 30).limit(30)).all()
    out = []
    for t in threads:
        part = db.scalar(select(MessageThreadParticipant).where(MessageThreadParticipant.thread_id == t.id, MessageThreadParticipant.user_id == p.user_id))
        unread = db.scalar(select(func.count()).where(Message.thread_id == t.id, Message.sender_id != p.user_id, Message.is_hidden.is_(False),
                                                      Message.created_at > (part.last_read_at or datetime(1970, 1, 1, tzinfo=timezone.utc))))
        names = db.scalars(select(User.full_name).join(MessageThreadParticipant, MessageThreadParticipant.user_id == User.id)
                           .where(MessageThreadParticipant.thread_id == t.id, User.id != p.user_id)).all()
        last = db.scalar(select(Message).where(Message.thread_id == t.id, Message.is_hidden.is_(False)).order_by(Message.created_at.desc()).limit(1))
        out.append({"id": t.id, "subject": t.subject, "thread_type": t.thread_type, "participants": names, "unread": unread,
                    "last_message": last.body[:140] if last else None, "last_message_at": t.last_message_at, "is_locked": t.is_locked})
    return out


@router.get("/messages/threads/{tid}")
def thread_messages(tid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("communication"))):
    t, part = _participant(db, p, tid)
    staff = p.can("messages.write")
    q = select(Message, User.full_name).outerjoin(User, User.id == Message.sender_id).where(Message.thread_id == t.id)
    if not staff:
        q = q.where(Message.is_hidden.is_(False))
    rows = db.execute(q.order_by(Message.created_at)).all()
    if part:
        part.last_read_at = datetime.now(timezone.utc)
        db.commit()
    return {"id": t.id, "subject": t.subject, "is_locked": t.is_locked, "can_moderate": staff,
            "messages": [{"id": m.id, "body": m.body, "sender": n, "mine": m.sender_id == p.user_id, "created_at": m.created_at,
                          "is_hidden": m.is_hidden, "reported": m.reported if staff else None} for m, n in rows]}


class MsgIn(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


@router.post("/messages/threads/{tid}", status_code=201)
def reply(tid: uuid.UUID, body: MsgIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("communication"))):
    t, part = _participant(db, p, tid)
    if part is None:
        raise Forbidden("Only participants can reply")
    if t.is_locked:
        raise Conflict("This conversation is locked")
    m = Message(institute_id=p.institute_id, thread_id=t.id, sender_id=p.user_id, body=body.body)
    db.add(m)
    t.last_message_at = datetime.now(timezone.utc)
    part.last_read_at = t.last_message_at
    outbox.emit(db, p.institute_id, "message.sent", "message_thread", t.id, {"sender": p.user.full_name if p.user else "", "subject": t.subject})
    db.commit()
    return {"id": m.id}


class ReportIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


@router.post("/messages/{mid}/report")
def report_message(mid: uuid.UUID, body: ReportIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("communication"))):
    m = get_tenant_obj(db, p, Message, mid, lock=True, label="Message")
    _participant(db, p, m.thread_id)
    m.reported = True
    m.report_reason = body.reason
    m.reported_by_id = p.user_id
    audit.record(db, p, "messages", m.id, "reported", reason=body.reason)
    db.commit()
    return {"ok": True}


class ModerateIn(BaseModel):
    hidden: bool | None = None
    lock_thread: bool | None = None


@router.post("/messages/{mid}/moderate")
def moderate_message(mid: uuid.UUID, body: ModerateIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("messages.write"))):
    m = get_tenant_obj(db, p, Message, mid, lock=True, label="Message")
    if body.hidden is not None:
        m.is_hidden = body.hidden
        m.moderated_by_id = p.user_id
    if body.lock_thread is not None:
        db.get(MessageThread, m.thread_id).is_locked = body.lock_thread
    audit.record(db, p, "messages", m.id, "moderate", new=body.model_dump(exclude_none=True))
    db.commit()
    return {"ok": True}


@router.get("/messages/reported")
def reported(db: Session = Depends(get_db), p: Principal = Depends(require_perm("messages.write"))):
    rows = db.execute(select(Message, User.full_name).outerjoin(User, User.id == Message.sender_id)
                      .where(Message.institute_id == p.institute_id, Message.reported.is_(True)).order_by(Message.created_at.desc()).limit(200)).all()
    return [{"id": m.id, "thread_id": m.thread_id, "body": m.body, "sender": n, "report_reason": m.report_reason, "is_hidden": m.is_hidden,
             "created_at": m.created_at} for m, n in rows]


# ----------------------------------------------------------------------------- notifications


@router.get("/notifications")
def my_notifications(unread_only: bool = False, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                     db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    q = select(Notification).where(Notification.user_id == p.user_id)
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [{"id": n.id, "event_type": n.event_type, "title": n.title, "body": n.body, "link": n.link, "is_read": n.is_read,
                       "created_at": n.created_at} for n in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/notifications/unread-count")
def unread_count(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    return {"count": db.scalar(select(func.count()).where(Notification.user_id == p.user_id, Notification.is_read.is_(False)))}


@router.post("/notifications/{nid}/read")
def mark_read(nid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    db.execute(update(Notification).where(Notification.id == nid, Notification.user_id == p.user_id)
               .values(is_read=True, read_at=datetime.now(timezone.utc)))
    db.commit()
    return {"ok": True}


@router.post("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    n = db.execute(update(Notification).where(Notification.user_id == p.user_id, Notification.is_read.is_(False))
                   .values(is_read=True, read_at=datetime.now(timezone.utc))).rowcount
    db.commit()
    return {"updated": n}


@router.get("/notifications/preferences")
def get_prefs(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    stored = {(x.event_type, x.channel): x.enabled for x in db.scalars(select(NotificationPreference).where(NotificationPreference.user_id == p.user_id))}
    from app.services.notifications import active_channels

    active = active_channels(db, p.institute_id) | {"in_app"}
    return {"channels": [{"channel": c, "available": c in active} for c in CHANNELS],
            "preferences": [{"event_type": e, "channel": c, "enabled": stored.get((e, c), True)} for e in NOTIFICATION_EVENTS for c in CHANNELS]}


class PrefIn(BaseModel):
    event_type: Literal[NOTIFICATION_EVENTS]  # type: ignore[valid-type]
    channel: Literal[CHANNELS]  # type: ignore[valid-type]
    enabled: bool


@router.put("/notifications/preferences")
def put_prefs(prefs: list[PrefIn], db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    for pr in prefs:
        stmt = insert(NotificationPreference).values(id=uuid.uuid4(), user_id=p.user_id, event_type=pr.event_type, channel=pr.channel, enabled=pr.enabled)
        db.execute(stmt.on_conflict_do_update(index_elements=["user_id", "event_type", "channel"], set_={"enabled": pr.enabled}))
    db.commit()
    return {"ok": True}


@router.get("/notifications/push-public-key")
def push_key(db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    cfg = registry.get_active(db, p.institute_id, "push")
    return {"public_key": cfg.config.get("vapid_public_key") if cfg else None}


class PushSubIn(BaseModel):
    endpoint: str = Field(max_length=1000, pattern=r"^https://")
    p256dh: str = Field(max_length=255)
    auth: str = Field(max_length=255)


@router.post("/notifications/push-subscription")
def push_subscribe(body: PushSubIn, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    stmt = insert(PushSubscription).values(id=uuid.uuid4(), user_id=p.user_id, endpoint=body.endpoint, p256dh=body.p256dh, auth=body.auth,
                                           user_agent=p.user_agent)
    db.execute(stmt.on_conflict_do_update(index_elements=["endpoint"], set_={"user_id": p.user_id, "p256dh": body.p256dh, "auth": body.auth}))
    db.commit()
    return {"ok": True}


@router.post("/notification-deliveries/{did}/retry")
def retry_delivery(did: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("notifications.write"))):
    d = db.scalar(select(NotificationDelivery).where(NotificationDelivery.id == did, NotificationDelivery.institute_id == p.institute_id))
    if d is None:
        raise NotFound("Delivery not found")
    if d.status not in ("failed", "cancelled"):
        raise Conflict("Only failed deliveries can be retried")
    d.status = "queued"
    d.attempts = 0
    d.next_attempt_at = datetime.now(timezone.utc)
    d.last_error = None
    audit.record(db, p, "notification_deliveries", d.id, "retry")
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------------- surveys


class SurveyStatusIn(BaseModel):
    status: Literal["open", "closed"]


@router.post("/surveys/{sid}/status", dependencies=[Depends(require_feature("communication"))])
def survey_status(sid: uuid.UUID, body: SurveyStatusIn, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    s = get_tenant_obj(db, p, Survey, sid, lock=True, label="Survey")
    if not (p.can("surveys.write") or s.created_by_id == p.user_id):
        raise Forbidden("You cannot change this survey")
    if body.status == "open" and not s.questions:
        raise ValidationFailed("Add questions before opening the survey")
    s.status = body.status
    audit.record(db, p, "surveys", s.id, f"survey_{body.status}")
    db.commit()
    return {"status": s.status}


class SurveyAnswerIn(BaseModel):
    answers: dict[str, Any]


@router.post("/surveys/{sid}/respond", dependencies=[Depends(require_feature("communication"))])
def survey_respond(sid: uuid.UUID, body: SurveyAnswerIn, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    res = REGISTRY["surveys"]
    mode = read_mode(p, res)
    s = db.scalar(base_query(p, res, mode).where(Survey.id == sid)) if mode else None
    if s is None or s.status != "open":
        raise NotFound("Survey is not open")
    now = datetime.now(timezone.utc)
    if (s.opens_at and now < s.opens_at) or (s.closes_at and now > s.closes_at):
        raise Conflict("Survey is outside its response window")
    keys = {q.get("key") for q in s.questions if isinstance(q, dict)}
    answers = {k: (str(v)[:2000] if not isinstance(v, (int, float, list)) else v) for k, v in body.answers.items() if k in keys}
    h = sha256_hex(f"{s.id}:{p.user_id}")
    stmt = insert(SurveyResponse).values(id=uuid.uuid4(), institute_id=p.institute_id, survey_id=s.id,
                                         respondent_id=None if s.is_anonymous else p.user_id, respondent_hash=h, answers=answers)
    if db.execute(stmt.on_conflict_do_nothing(index_elements=["survey_id", "respondent_hash"]).returning(SurveyResponse.id)).first() is None:
        raise Conflict("You have already responded")
    db.commit()
    return {"ok": True}


@router.get("/surveys/{sid}/summary", dependencies=[Depends(require_feature("communication"))])
def survey_summary(sid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    s = get_tenant_obj(db, p, Survey, sid, label="Survey")
    if not (p.can("surveys.read") or s.created_by_id == p.user_id):
        raise Forbidden("You cannot view survey results")
    responses = db.scalars(select(SurveyResponse.answers).where(SurveyResponse.survey_id == s.id)).all()
    summary = []
    for q in s.questions or []:
        if not isinstance(q, dict):
            continue
        vals = [r.get(q.get("key")) for r in responses if r.get(q.get("key")) is not None]
        entry: dict[str, Any] = {"key": q.get("key"), "label": q.get("label"), "type": q.get("type"), "responses": len(vals)}
        if q.get("type") == "rating":
            nums = [float(v) for v in vals if isinstance(v, (int, float)) or str(v).replace(".", "", 1).isdigit()]
            entry["average"] = round(sum(nums) / len(nums), 2) if nums else None
        elif q.get("type") == "choice":
            entry["counts"] = dict(Counter(str(v) for v in vals))
        else:
            entry["samples"] = [str(v)[:300] for v in vals[:50]]
        summary.append(entry)
    return {"survey": s.title, "total_responses": len(responses), "anonymous": s.is_anonymous, "questions": summary}
