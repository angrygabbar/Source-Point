"""Celery tasks: outbox dispatch, notification delivery, scheduled automations and exports."""

import ipaddress
import json
import socket
import uuid
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import and_, case, delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import decrypt_secret, hmac_sha256_hex
from app.db.session import SessionLocal
from app.integrations import providers, registry
from app.models import (
    Announcement,
    Assignment,
    AssignmentTarget,
    BackgroundJob,
    BookLoan,
    ClassSession,
    ClassSessionTeacher,
    Enquiry,
    EventOutbox,
    ExamResult,
    Examination,
    FollowUp,
    Institute,
    Invoice,
    LibraryMember,
    LoginHistory,
    Material,
    MessageThreadParticipant,
    Notification,
    NotificationDelivery,
    Parent,
    Payment,
    PushSubscription,
    Role,
    Student,
    StudentAttendance,
    StudentEnrollment,
    StudentParent,
    Submission,
    SyllabusChapter,
    SyllabusProgress,
    Teacher,
    UsageRecord,
    User,
    UserRole,
    WebhookDelivery,
    WebhookEndpoint,
)
from app.services import app_settings, finance, notifications, storage
from app.services.notifications import notify, staff_user_ids, student_and_parent_user_ids
from app.services.scheduling import generate_sessions, today_local
from app.workers.celery_app import celery_app

log = get_logger("classflow.worker")
MAX_OUTBOX_ATTEMPTS = 8


def _institutes(db: Session):
    return db.scalars(select(Institute).where(Institute.is_active.is_(True))).all()


def _batch_student_ids(db: Session, batch_ids, on: date | None = None) -> list[uuid.UUID]:
    q = select(StudentEnrollment.student_id).where(StudentEnrollment.batch_id.in_(batch_ids), StudentEnrollment.status == "active")
    return list(set(db.scalars(q)))


def _teacher_user_ids(db: Session, teacher_ids) -> list[uuid.UUID]:
    return [u for u in db.scalars(select(Teacher.user_id).where(Teacher.id.in_(teacher_ids))) if u]


def _fmt_money(v) -> str:
    return f"Rs. {v:,.2f}"


# ----------------------------------------------------------------------------- outbox handlers


def handle_event(db: Session, ev: EventOutbox) -> None:
    I, t, pl, aid = ev.institute_id, ev.event_type, ev.payload or {}, ev.aggregate_id
    inst = db.get(Institute, I) if I else None
    ctx = {"institute": inst.name if inst else ""}
    if t == "invoice.issued":
        inv = db.get(Invoice, aid)
        if inv:
            notify(db, I, student_and_parent_user_ids(db, [inv.student_id]), "fee_due", f"New invoice {inv.invoice_number}",
                   f"Amount {_fmt_money(inv.total)} due on {inv.due_date:%d-%m-%Y}.", link=f"/finance/invoices/{inv.id}",
                   dedupe_key=f"inv:{inv.id}", context={**ctx, "invoice_number": inv.invoice_number, "amount": _fmt_money(inv.total),
                                                        "due_date": f"{inv.due_date:%d-%m-%Y}"})
    elif t == "payment.received":
        pay = db.get(Payment, aid)
        if pay:
            notify(db, I, student_and_parent_user_ids(db, [pay.student_id]), "payment_received", f"Payment received {pay.receipt_number}",
                   f"We received {_fmt_money(pay.amount)}. Thank you.", link=f"/r/payments/{pay.id}", dedupe_key=f"pay:{pay.id}",
                   context={**ctx, "receipt_number": pay.receipt_number, "amount": _fmt_money(pay.amount)})
    elif t in ("session.cancelled", "session.rescheduled"):
        s = db.get(ClassSession, aid)
        if s:
            users = student_and_parent_user_ids(db, _batch_student_ids(db, [s.batch_id]))
            tids = set(db.scalars(select(ClassSessionTeacher.teacher_id).where(ClassSessionTeacher.session_id == s.id))) | {s.scheduled_teacher_id}
            users += _teacher_user_ids(db, tids)
            if t == "session.cancelled":
                notify(db, I, users, "class_cancelled", "Class cancelled", f"The class on {s.session_date:%d-%m-%Y} was cancelled: {pl.get('reason', '')}",
                       link=f"/sessions/{s.id}", dedupe_key=f"cancel:{s.id}", context=ctx)
            else:
                new = db.get(ClassSession, uuid.UUID(pl["new_session_id"])) if pl.get("new_session_id") else None
                when = f" to {new.session_date:%d-%m-%Y}" if new else ""
                notify(db, I, users, "class_rescheduled", "Class rescheduled", f"The class on {s.session_date:%d-%m-%Y} moved{when}. {pl.get('reason', '')}",
                       link=f"/sessions/{new.id if new else s.id}", dedupe_key=f"resched:{s.id}:{pl.get('new_session_id')}", context=ctx)
    elif t == "attendance.submitted":
        s = db.get(ClassSession, aid)
        if s:
            subject = db.scalar(text("select name from subjects where id = :i"), {"i": s.subject_id})
            for st in db.scalars(select(StudentAttendance).where(StudentAttendance.session_id == s.id, StudentAttendance.status == "absent")):
                student = db.get(Student, st.student_id)
                notify(db, I, student_and_parent_user_ids(db, [st.student_id]), "student_absence", f"Absent: {student.full_name}",
                       f"{student.full_name} was marked absent for {subject} on {s.session_date:%d-%m-%Y}.", link="/dashboard",
                       dedupe_key=f"absent:{s.id}:{st.student_id}",
                       context={**ctx, "student_name": student.full_name, "status": "absent", "subject": subject, "date": f"{s.session_date:%d-%m-%Y}"})
    elif t == "teacher.absent":
        s = db.get(ClassSession, aid)
        if s:
            notify(db, I, staff_user_ids(db, I), "teacher_absence", "Teacher absent", f"Teacher absent for class on {s.session_date:%d-%m-%Y}. Assign a substitute or makeup.",
                   link=f"/sessions/{s.id}", dedupe_key=f"tabsent:{s.id}")
    elif t == "material.uploaded":
        m = db.get(Material, aid)
        if m and m.batch_id and m.visibility in ("batch", "institute"):
            users = [u for u in db.scalars(select(Student.user_id).where(Student.id.in_(_batch_student_ids(db, [m.batch_id])))) if u]
            notify(db, I, users, "material_uploaded", "New study material", m.title, link="/materials", dedupe_key=f"mat:{m.id}")
    elif t == "assignment.published":
        a = db.get(Assignment, aid)
        if a:
            targets = db.scalars(select(AssignmentTarget).where(AssignmentTarget.assignment_id == a.id)).all()
            sids = set(_batch_student_ids(db, [x.batch_id for x in targets if x.batch_id])) | {x.student_id for x in targets if x.student_id}
            notify(db, I, student_and_parent_user_ids(db, sids), "assignment_published", f"New homework: {a.title}",
                   f"Due {a.due_at:%d-%m-%Y %H:%M} UTC", link=f"/assignments/{a.id}", dedupe_key=f"asg:{a.id}",
                   context={**ctx, "title": a.title})
    elif t == "submission.received":
        sub = db.get(Submission, aid)
        if sub:
            a = db.get(Assignment, sub.assignment_id)
            st = db.get(Student, sub.student_id)
            notify(db, I, _teacher_user_ids(db, [a.teacher_id]), "submission_received", f"Submission: {a.title}",
                   f"{st.full_name} submitted{' late' if sub.is_late else ''}.", link=f"/assignments/{a.id}", dedupe_key=f"subrec:{sub.id}:{sub.current_version}")
    elif t == "submission.evaluated":
        sub = db.get(Submission, aid)
        if sub:
            a = db.get(Assignment, sub.assignment_id)
            notify(db, I, student_and_parent_user_ids(db, [sub.student_id]), "submission_evaluated", f"Homework evaluated: {a.title}",
                   "Marks and feedback are available.", link=f"/assignments/{a.id}", dedupe_key=f"eval:{ev.id}")
    elif t == "announcement.published":
        a = db.get(Announcement, aid)
        if a:
            users: set[uuid.UUID] = set()
            all_users = select(User.id).where(User.institute_id == I, User.is_active.is_(True))
            role_users = lambda portal: set(db.scalars(select(UserRole.user_id).join(Role, Role.id == UserRole.role_id).join(User, User.id == UserRole.user_id)
                                                       .where(Role.portal == portal, User.institute_id == I)))  # noqa: E731
            if a.audience == "all":
                users = set(db.scalars(all_users))
            elif a.audience == "staff":
                users = role_users("admin") | role_users("teacher")
            elif a.audience == "teachers":
                users = role_users("teacher")
            elif a.audience == "students":
                users = role_users("student")
            elif a.audience == "parents":
                users = role_users("parent")
            elif a.audience == "batch" and a.batch_id:
                sids = _batch_student_ids(db, [a.batch_id])
                users = set(student_and_parent_user_ids(db, sids))
            notify(db, I, users, "announcement", a.title, a.body[:500], link="/announcements", dedupe_key=f"ann:{a.id}",
                   context={**ctx, "title": a.title, "body": a.body})
    elif t == "admission.enquiry":
        e = db.get(Enquiry, aid)
        if e and e.assigned_to_id:
            notify(db, I, [e.assigned_to_id], "admission", "New enquiry", e.contact_name or "", link="/admissions", dedupe_key=f"enq:{e.id}")
    elif t == "admission.converted":
        notify(db, I, staff_user_ids(db, I), "admission", "New admission", pl.get("name", ""), link=f"/students/{aid}", dedupe_key=f"adm:{aid}")
    elif t == "message.sent":
        users = [u for u in db.scalars(select(MessageThreadParticipant.user_id).where(MessageThreadParticipant.thread_id == aid))]
        notify(db, I, users, "message", f"New message: {pl.get('subject', '')}", f"From {pl.get('sender', '')}", link=f"/messages?thread={aid}")
    elif t == "exam.results_published":
        e = db.get(Examination, aid)
        if e:
            sids = list(db.scalars(select(ExamResult.student_id).where(ExamResult.examination_id == e.id)))
            notify(db, I, student_and_parent_user_ids(db, sids), "exam_results", f"Results published: {e.name}", "", link=f"/exams/{e.id}",
                   dedupe_key=f"res:{e.id}")
    _queue_webhooks(db, ev)


def _queue_webhooks(db: Session, ev: EventOutbox) -> None:
    if not ev.institute_id:
        return
    for ep in db.scalars(select(WebhookEndpoint).where(WebhookEndpoint.institute_id == ev.institute_id, WebhookEndpoint.is_active.is_(True))):
        if "*" in (ep.events or []) or ev.event_type in (ep.events or []):
            db.add(WebhookDelivery(institute_id=ev.institute_id, endpoint_id=ep.id, event_type=ev.event_type, status="pending",
                                   payload={"id": str(ev.id), "type": ev.event_type, "aggregate": ev.aggregate_type,
                                            "aggregate_id": str(ev.aggregate_id) if ev.aggregate_id else None, "data": ev.payload,
                                            "occurred_at": ev.created_at.isoformat() if ev.created_at else None},
                                   next_attempt_at=datetime.now(timezone.utc)))


@celery_app.task(name="app.workers.tasks.dispatch_outbox")
def dispatch_outbox() -> int:
    processed = 0
    with SessionLocal() as db:
        events = db.scalars(select(EventOutbox).where(EventOutbox.status.in_(("pending", "failed")), EventOutbox.attempts < MAX_OUTBOX_ATTEMPTS,
                                                      EventOutbox.available_at <= datetime.now(timezone.utc))
                            .order_by(EventOutbox.created_at).limit(100).with_for_update(skip_locked=True)).all()
        for ev in events:
            try:
                with db.begin_nested():
                    handle_event(db, ev)
                ev.status = "processed"
                ev.processed_at = datetime.now(timezone.utc)
            except Exception as exc:  # noqa: BLE001
                ev.attempts += 1
                ev.status = "failed"
                ev.last_error = type(exc).__name__
                ev.available_at = datetime.now(timezone.utc) + timedelta(seconds=30 * (2 ** ev.attempts))
                log.warning("outbox event failed", extra={"ctx": {"event": ev.event_type, "error": type(exc).__name__}})
            processed += 1
        db.commit()
    return processed


# ----------------------------------------------------------------------------- notification delivery


def _deliver(db: Session, d: NotificationDelivery) -> str:
    cfg = registry.get_active(db, d.institute_id, d.channel)
    if cfg is None:
        raise providers.ProviderError(f"{d.channel} provider is not configured")
    d.provider = cfg.provider
    if d.channel == "email":
        return providers.send_email(cfg, d.recipient, d.subject or "ClassFlow notification", d.body or "")
    if d.channel == "sms":
        return providers.send_sms(cfg, d.recipient, d.body or "")
    if d.channel == "whatsapp":
        return providers.send_whatsapp(cfg, d.recipient, d.body or "")
    if d.channel == "push":
        subs = db.scalars(select(PushSubscription).where(PushSubscription.user_id == d.user_id)).all()
        if not subs:
            raise providers.ProviderError("User has no push subscriptions")
        for s in subs:
            providers.send_push(cfg, {"endpoint": s.endpoint, "keys": {"p256dh": s.p256dh, "auth": s.auth}}, d.subject or "", d.body or "", None)
        return f"{len(subs)} subscriptions"
    raise providers.ProviderError("Unknown channel")


@celery_app.task(name="app.workers.tasks.send_deliveries")
def send_deliveries() -> int:
    sent = 0
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        rows = db.scalars(select(NotificationDelivery).where(NotificationDelivery.status == "queued", NotificationDelivery.next_attempt_at <= now)
                          .order_by(NotificationDelivery.created_at).limit(50).with_for_update(skip_locked=True)).all()
        for d in rows:
            d.attempts += 1
            try:
                d.provider_message_id = (_deliver(db, d) or "")[:255]
                d.status = "sent"
                d.sent_at = datetime.now(timezone.utc)
                d.last_error = None
                sent += 1
            except Exception as exc:  # noqa: BLE001
                d.last_error = str(exc)[:500] if isinstance(exc, providers.ProviderError) else type(exc).__name__
                if d.attempts >= d.max_attempts:
                    d.status = "failed"
                else:
                    d.next_attempt_at = datetime.now(timezone.utc) + timedelta(minutes=2 ** d.attempts)
            db.commit()
    return sent


def _safe_url(url: str) -> bool:
    try:
        u = urlparse(url)
        if u.scheme != "https" or not u.hostname:
            return False
        for info in socket.getaddrinfo(u.hostname, u.port or 443):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
    except (OSError, ValueError):
        return False


@celery_app.task(name="app.workers.tasks.send_webhooks")
def send_webhooks() -> int:
    n = 0
    with SessionLocal() as db:
        rows = db.scalars(select(WebhookDelivery).where(WebhookDelivery.status == "pending", WebhookDelivery.next_attempt_at <= datetime.now(timezone.utc))
                          .limit(50).with_for_update(skip_locked=True)).all()
        for d in rows:
            ep = db.get(WebhookEndpoint, d.endpoint_id)
            d.attempts += 1
            body = json.dumps(d.payload, default=str).encode()
            try:
                if not _safe_url(ep.url):
                    raise ValueError("Webhook URL must be public https")
                secret = decrypt_secret(ep.secret_encrypted) or ""
                r = httpx.post(ep.url, content=body, timeout=10, headers={"Content-Type": "application/json", "X-ClassFlow-Event": d.event_type,
                                                                          "X-ClassFlow-Signature": hmac_sha256_hex(secret, body) if secret else ""})
                d.response_status = r.status_code
                if r.status_code < 300:
                    d.status, d.delivered_at = "delivered", datetime.now(timezone.utc)
                else:
                    raise ValueError(f"HTTP {r.status_code}")
            except Exception as exc:  # noqa: BLE001
                d.last_error = str(exc)[:300]
                if d.attempts >= 6:
                    d.status = "failed"
                else:
                    d.next_attempt_at = datetime.now(timezone.utc) + timedelta(minutes=2 ** d.attempts)
            n += 1
            db.commit()
    return n


# ----------------------------------------------------------------------------- scheduled automations


@celery_app.task(name="app.workers.tasks.generate_upcoming_sessions")
def generate_upcoming_sessions() -> dict:
    out = {}
    with SessionLocal() as db:
        for inst in _institutes(db):
            today = today_local(db, inst.id)
            out[inst.code] = generate_sessions(db, inst.id, today, today + timedelta(days=21))
            db.commit()
    return out


@celery_app.task(name="app.workers.tasks.daily_finance")
def daily_finance() -> dict:
    out = {}
    with SessionLocal() as db:
        for inst in _institutes(db):
            I = inst.id
            today = today_local(db, I)
            r: dict = {"overdue_refreshed": finance.refresh_overdue(db, I, today)}
            r["late_fees"] = finance.apply_late_fees(db, I, today)
            if app_settings.get(db, I, "billing.auto_generate_invoices"):
                r["scheduled"] = finance.generate_scheduled_invoices(db, I, today + timedelta(days=int(app_settings.get(db, I, "billing.invoice_lead_days") or 0)))
            r["per_class"] = finance.generate_per_class_charges(db, I, today - timedelta(days=14), today)
            week = today.isocalendar()[1]
            for inv in db.scalars(select(Invoice).where(Invoice.institute_id == I, Invoice.status.in_(("issued", "partially_paid")),
                                                        Invoice.due_date == today + timedelta(days=3))):
                notify(db, I, student_and_parent_user_ids(db, [inv.student_id]), "fee_due", f"Fee due soon: {inv.invoice_number}",
                       f"{_fmt_money(inv.balance_due)} due on {inv.due_date:%d-%m-%Y}.", link=f"/finance/invoices/{inv.id}", dedupe_key=f"due3:{inv.id}",
                       context={"institute": inst.name, "invoice_number": inv.invoice_number, "amount": _fmt_money(inv.balance_due), "due_date": f"{inv.due_date:%d-%m-%Y}"})
            for inv in db.scalars(select(Invoice).where(Invoice.institute_id == I, Invoice.status == "overdue", Invoice.balance_due > 0)):
                notify(db, I, student_and_parent_user_ids(db, [inv.student_id]), "fee_overdue", f"Overdue: {inv.invoice_number}",
                       f"{_fmt_money(inv.balance_due)} was due on {inv.due_date:%d-%m-%Y}.", link=f"/finance/invoices/{inv.id}",
                       dedupe_key=f"overdue:{inv.id}:{today.year}-{week}",
                       context={"institute": inst.name, "invoice_number": inv.invoice_number, "amount": _fmt_money(inv.balance_due), "due_date": f"{inv.due_date:%d-%m-%Y}"})
            db.commit()
            out[inst.code] = r
    return out


@celery_app.task(name="app.workers.tasks.daily_academic_alerts")
def daily_academic_alerts() -> dict:
    out = {}
    with SessionLocal() as db:
        for inst in _institutes(db):
            I = inst.id
            today = today_local(db, I)
            week = f"{today.year}-{today.isocalendar()[1]}"
            threshold = app_settings.get(db, I, "attendance.alert_threshold_percent")
            low = 0
            for sid, total, present in db.execute(
                select(StudentAttendance.student_id, func.count(), func.sum(case((StudentAttendance.status.in_(("present", "late")), 1), else_=0)))
                .join(ClassSession, ClassSession.id == StudentAttendance.session_id)
                .where(StudentAttendance.institute_id == I, ClassSession.session_date >= today - timedelta(days=30))
                .group_by(StudentAttendance.student_id).having(func.count() >= 4)).all():
                pct = (present or 0) * 100 / total
                if pct < threshold:
                    st = db.get(Student, sid)
                    notify(db, I, student_and_parent_user_ids(db, [sid]) + staff_user_ids(db, I, ("institute_admin",)), "attendance_alert",
                           f"Low attendance: {st.full_name}", f"Attendance is {pct:.0f}% over the last 30 days (threshold {threshold}%).",
                           link=f"/students/{sid}", dedupe_key=f"lowatt:{sid}:{week}")
                    low += 1
            delay_days = app_settings.get(db, I, "syllabus.delay_alert_days")
            delayed = 0
            for prog in db.scalars(select(SyllabusProgress).where(SyllabusProgress.institute_id == I, SyllabusProgress.status != "completed",
                                                                  SyllabusProgress.planned_end < today - timedelta(days=delay_days))):
                ch = db.get(SyllabusChapter, prog.chapter_id)
                users = _teacher_user_ids(db, [prog.teacher_id]) if prog.teacher_id else []
                notify(db, I, users + staff_user_ids(db, I, ("academic_coordinator",)), "syllabus_delay", "Syllabus delayed",
                       f"Chapter '{ch.title}' passed its planned end {prog.planned_end:%d-%m-%Y}.", link="/syllabus",
                       dedupe_key=f"sydelay:{prog.id}:{week}")
                delayed += 1
            eval_days = app_settings.get(db, I, "evaluation.pending_alert_days")
            pend = 0
            for a_id, teacher_id, title, cnt in db.execute(
                select(Assignment.id, Assignment.teacher_id, Assignment.title, func.count(Submission.id)).join(Submission, Submission.assignment_id == Assignment.id)
                .where(Assignment.institute_id == I, Submission.status.in_(("submitted", "late", "under_review")),
                       Submission.submitted_at < datetime.now(timezone.utc) - timedelta(days=eval_days)).group_by(Assignment.id)).all():
                notify(db, I, _teacher_user_ids(db, [teacher_id]), "evaluation_pending", f"Evaluations pending: {title}",
                       f"{cnt} submission(s) awaiting evaluation for more than {eval_days} days.", link=f"/assignments/{a_id}",
                       dedupe_key=f"evalpend:{a_id}:{today}")
                pend += 1
            db.commit()
            out[inst.code] = {"low_attendance": low, "syllabus_delays": delayed, "pending_evaluations": pend}
    return out


@celery_app.task(name="app.workers.tasks.homework_reminders")
def homework_reminders() -> int:
    n = 0
    with SessionLocal() as db:
        now = datetime.now(timezone.utc)
        for inst in _institutes(db):
            hours = app_settings.get(db, inst.id, "homework.reminder_hours_before_due")
            for a in db.scalars(select(Assignment).where(Assignment.institute_id == inst.id, Assignment.status == "submission_open",
                                                         Assignment.due_at.between(now, now + timedelta(hours=hours)))):
                targets = db.scalars(select(AssignmentTarget).where(AssignmentTarget.assignment_id == a.id)).all()
                sids = set(_batch_student_ids(db, [x.batch_id for x in targets if x.batch_id])) | {x.student_id for x in targets if x.student_id}
                done = set(db.scalars(select(Submission.student_id).where(Submission.assignment_id == a.id, Submission.status.notin_(("draft", "resubmission_requested")))))
                pending = sids - done
                if pending:
                    users = [u for u in db.scalars(select(Student.user_id).where(Student.id.in_(pending))) if u]
                    n += notify(db, inst.id, users, "homework_deadline", f"Homework due soon: {a.title}", f"Due {a.due_at:%d-%m-%Y %H:%M} UTC",
                                link=f"/assignments/{a.id}", dedupe_key=f"hwdue:{a.id}")
            db.commit()
    return n


@celery_app.task(name="app.workers.tasks.follow_up_reminders")
def follow_up_reminders() -> int:
    n = 0
    with SessionLocal() as db:
        now = datetime.now(timezone.utc)
        for f in db.scalars(select(FollowUp).where(FollowUp.status == "pending", FollowUp.reminder_sent_at.is_(None),
                                                   FollowUp.due_at <= now + timedelta(minutes=60)).limit(500)):
            e = db.get(Enquiry, f.enquiry_id)
            if f.assigned_to_id:
                notify(db, f.institute_id, [f.assigned_to_id], "follow_up_due", f"Follow-up: {e.contact_name}", f"{f.mode} due {f.due_at:%d-%m-%Y %H:%M} UTC",
                       link="/admissions", dedupe_key=f"fu:{f.id}")
            f.reminder_sent_at = now
            n += 1
        db.commit()
    return n


@celery_app.task(name="app.workers.tasks.library_reminders")
def library_reminders() -> int:
    n = 0
    with SessionLocal() as db:
        today = date.today()
        for loan in db.scalars(select(BookLoan).where(BookLoan.status.in_(("issued", "overdue")), BookLoan.due_date <= today + timedelta(days=1))):
            if loan.due_date < today:
                loan.status = "overdue"
            member = db.get(LibraryMember, loan.member_id)
            uid = member.user_id
            if not uid and member.student_id:
                uid = db.scalar(select(Student.user_id).where(Student.id == member.student_id))
            if uid:
                notify(db, loan.institute_id, [uid], "system", "Library book due" if loan.due_date >= today else "Library book overdue",
                       f"Please return the book by {loan.due_date:%d-%m-%Y}.", dedupe_key=f"lib:{loan.id}:{today}")
            n += 1
        db.commit()
    return n


@celery_app.task(name="app.workers.tasks.finalise_exam_attempts")
def finalise_exam_attempts() -> int:
    from app.api.v1.exams import finalise_all_expired

    with SessionLocal() as db:
        n = finalise_all_expired(db)
        db.commit()
    return n


@celery_app.task(name="app.workers.tasks.usage_and_retention")
def usage_and_retention() -> dict:
    out = {}
    with SessionLocal() as db:
        period = date.today().strftime("%Y-%m")
        for inst in _institutes(db):
            metrics = {
                "students": db.scalar(select(func.count()).where(Student.institute_id == inst.id, Student.status == "active")),
                "teachers": db.scalar(select(func.count()).where(Teacher.institute_id == inst.id, Teacher.employment_status == "active")),
            }
            try:
                metrics["storage_bytes"] = storage.bucket_usage_bytes(inst.id)
            except Exception:  # noqa: BLE001
                pass
            for metric, qty in metrics.items():
                row = db.scalar(select(UsageRecord).where(UsageRecord.institute_id == inst.id, UsageRecord.metric == metric, UsageRecord.period == period))
                if row is None:
                    row = UsageRecord(institute_id=inst.id, metric=metric, period=period, cost=0)
                    db.add(row)
                row.quantity = qty
            notif_days = app_settings.get(db, inst.id, "retention.notification_days")
            if notif_days:
                db.execute(delete(Notification).where(Notification.institute_id == inst.id, Notification.is_read.is_(True),
                                                      Notification.created_at < datetime.now(timezone.utc) - timedelta(days=notif_days)))
            login_days = app_settings.get(db, inst.id, "retention.login_history_days")
            if login_days:
                db.execute(delete(LoginHistory).where(LoginHistory.institute_id == inst.id,
                                                      LoginHistory.created_at < datetime.now(timezone.utc) - timedelta(days=login_days)))
            db.commit()
            out[inst.code] = metrics
    return out


@celery_app.task(name="app.workers.tasks.run_export", bind=True, max_retries=2)
def run_export(self, job_id: str) -> str:
    from app.api.deps import _load_principal
    from app.crud.engine import REGISTRY, apply_filters, apply_sort, base_query, export_rows, read_mode
    from starlette.datastructures import QueryParams

    with SessionLocal() as db:
        job = db.get(BackgroundJob, uuid.UUID(job_id))
        if job is None or job.status != "queued":
            return "skipped"
        job.status, job.started_at = "running", datetime.now(timezone.utc)
        db.commit()
        try:
            user = db.get(User, uuid.UUID(job.params["user_id"]))

            class _Req:  # minimal request shim for principal loading
                headers = {"x-branch-id": job.params.get("branch_id") or ""}
                client = None

            p = _load_principal(db, user, job.institute_id, _Req())
            res = REGISTRY[job.params["resource"]]
            mode = read_mode(p, res)
            if mode is None:
                raise PermissionError("No longer permitted")
            q = apply_filters(base_query(p, res, mode), res, QueryParams(job.params.get("filters") or {}))
            rows = db.scalars(apply_sort(q, res, (job.params.get("filters") or {}).get("sort"))).all()
            data, filename, mime = export_rows(db, p, res, rows, job.params["format"])
            stored = storage.put_bytes(job.institute_id, "exports", filename, data, mime)
            job.result_object_key, job.result_filename = stored.object_key, filename
            job.result = {"rows": len(rows)}
            job.status, job.progress = "succeeded", 100
            notify(db, job.institute_id, [user.id], "system", "Export ready", f"{res.label}: {len(rows)} rows", link=f"/jobs/{job.id}")
        except Exception as exc:  # noqa: BLE001
            job.status, job.error = "failed", type(exc).__name__
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        return job.status
