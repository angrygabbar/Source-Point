import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.api.common import ensure_session_access, get_tenant_obj, teacher_can_handle_session
from app.api.deps import Principal, get_principal, require_feature, require_perm
from app.core.errors import Conflict, Forbidden, ValidationFailed
from app.crud.engine import REGISTRY, base_query, read_mode
from app.db.session import get_db
from app.models import (
    Assignment,
    AttendanceAuditLog,
    AttendanceCorrection,
    Batch,
    ClassSchedule,
    ClassSession,
    ClassSessionTeacher,
    Classroom,
    EnrollmentSubject,
    LessonPlan,
    Material,
    Student,
    StudentAttendance,
    StudentEnrollment,
    Subject,
    SyllabusChapter,
    SyllabusProgress,
    Teacher,
    TeacherAttendance,
)
from app.services import audit, notifications, outbox, scheduling

router = APIRouter(tags=["Class operations"])

HHMM = r"^([01][0-9]|2[0-3]):[0-5][0-9]$"


def _session(db: Session, p: Principal, sid: uuid.UUID, write: bool = False, lock: bool = False) -> ClassSession:
    s = get_tenant_obj(db, p, ClassSession, sid, lock=lock, label="Class session")
    ensure_session_access(db, p, s, write)
    return s


def _labels(db: Session, sessions: list[ClassSession]) -> dict:
    def names(model, ids, col="name"):
        ids = {i for i in ids if i}
        if not ids:
            return {}
        return dict(db.execute(select(model.id, getattr(model, col)).where(model.id.in_(ids))).all())

    subs = db.execute(
        select(ClassSessionTeacher.session_id, ClassSessionTeacher.teacher_id).where(
            ClassSessionTeacher.session_id.in_([s.id for s in sessions]), ClassSessionTeacher.role == "substitute"
        )
    ).all() if sessions else []
    sub_map: dict[uuid.UUID, list[uuid.UUID]] = {}
    for sid, tid in subs:
        sub_map.setdefault(sid, []).append(tid)
    teacher_ids = {s.scheduled_teacher_id for s in sessions} | {t for v in sub_map.values() for t in v}
    return {
        "batches": names(Batch, {s.batch_id for s in sessions}),
        "subjects": names(Subject, {s.subject_id for s in sessions}),
        "teachers": names(Teacher, teacher_ids, "full_name"),
        "rooms": names(Classroom, {s.classroom_id for s in sessions}),
        "subs": sub_map,
    }


def session_out(s: ClassSession, L: dict) -> dict:
    subs = L["subs"].get(s.id, [])
    return {
        "id": s.id, "session_date": s.session_date, "start": s.scheduled_start, "end": s.scheduled_end,
        "actual_start": s.actual_start, "actual_end": s.actual_end, "status": s.status, "session_type": s.session_type,
        "batch_id": s.batch_id, "batch": L["batches"].get(s.batch_id), "subject_id": s.subject_id, "subject": L["subjects"].get(s.subject_id),
        "scheduled_teacher_id": s.scheduled_teacher_id, "teacher": L["teachers"].get(s.scheduled_teacher_id),
        "substitutes": [{"id": t, "name": L["teachers"].get(t)} for t in subs],
        "classroom_id": s.classroom_id, "classroom": L["rooms"].get(s.classroom_id), "attendance_state": s.attendance_state,
        "cancellation_reason": s.cancellation_reason, "remarks": s.remarks, "topic_covered": s.topic_covered,
        "online_meeting_url": s.online_meeting_url, "branch_id": s.branch_id, "schedule_id": s.schedule_id,
        "makeup_for_session_id": s.makeup_for_session_id, "rescheduled_from_session_id": s.rescheduled_from_session_id,
        "syllabus_chapter_id": s.syllabus_chapter_id,
    }


# ----------------------------------------------------------------------------- calendar & schedules


@router.get("/class-sessions/calendar")
def calendar(
    start: date,
    end: date,
    teacher_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
    subject_id: uuid.UUID | None = None,
    classroom_id: uuid.UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    p: Principal = Depends(get_principal),
):
    if (end - start).days > 93:
        raise ValidationFailed("Calendar range is limited to 3 months")
    res = REGISTRY["class-sessions"]
    mode = read_mode(p, res)
    if mode is None:
        raise Forbidden("You cannot view the timetable")
    q = base_query(p, res, mode).where(ClassSession.session_date.between(start, end))
    if teacher_id:
        q = q.where(or_(ClassSession.scheduled_teacher_id == teacher_id,
                        ClassSession.id.in_(select(ClassSessionTeacher.session_id).where(ClassSessionTeacher.teacher_id == teacher_id))))
    if batch_id:
        q = q.where(ClassSession.batch_id == batch_id)
    if subject_id:
        q = q.where(ClassSession.subject_id == subject_id)
    if classroom_id:
        q = q.where(ClassSession.classroom_id == classroom_id)
    if status:
        q = q.where(ClassSession.status.in_(status.split(",")))
    rows = db.scalars(q.order_by(ClassSession.scheduled_start).limit(3000)).all()
    L = _labels(db, rows)
    return [session_out(s, L) for s in rows]


class GenerateIn(BaseModel):
    start_date: date
    end_date: date
    schedule_ids: list[uuid.UUID] | None = None


@router.post("/schedules/generate-sessions")
def generate(body: GenerateIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("schedules.write"))):
    if body.end_date < body.start_date or (body.end_date - body.start_date).days > 180:
        raise ValidationFailed("Choose a range of up to 180 days")
    r = scheduling.generate_sessions(db, p.institute_id, body.start_date, body.end_date, body.schedule_ids, p.user_id)
    audit.record(db, p, "class_sessions", None, "generate", new={**r, "from": body.start_date, "to": body.end_date})
    db.commit()
    return r


class ConflictCheckIn(BaseModel):
    teacher_id: uuid.UUID | None = None
    batch_id: uuid.UUID | None = None
    classroom_id: uuid.UUID | None = None
    session_date: date
    start_time: str = Field(pattern=HHMM)
    end_time: str = Field(pattern=HHMM)
    exclude_session_id: uuid.UUID | None = None


@router.post("/class-sessions/check-conflicts")
def check_conflicts(body: ConflictCheckIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("sessions.write", "sessions.write_own"))):
    tz = scheduling.institute_tz(db, p.institute_id)
    st, en = scheduling.local_to_utc(body.session_date, body.start_time, tz), scheduling.local_to_utc(body.session_date, body.end_time, tz)
    return {"conflicts": scheduling.session_conflicts(db, p.institute_id, st, en, {body.teacher_id} if body.teacher_id else set(),
                                                      body.batch_id, body.classroom_id, body.exclude_session_id)}


class SessionCreate(BaseModel):
    batch_id: uuid.UUID
    subject_id: uuid.UUID
    teacher_id: uuid.UUID
    classroom_id: uuid.UUID | None = None
    session_date: date
    start_time: str = Field(pattern=HHMM)
    end_time: str = Field(pattern=HHMM)
    session_type: Literal["makeup", "extra", "demo", "exam", "doubt_solving", "regular"] = "extra"
    makeup_for_session_id: uuid.UUID | None = None
    online_meeting_url: str | None = Field(default=None, max_length=500)
    remarks: str | None = None
    override_reason: str | None = Field(default=None, max_length=1000)


@router.post("/class-sessions", status_code=201)
def create_session(body: SessionCreate, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    batch = get_tenant_obj(db, p, Batch, body.batch_id, label="Batch")
    if not (p.can("sessions.write") or (p.can("sessions.write_own") and (body.teacher_id == p.teacher_id and batch.id in p.batch_ids))):
        raise Forbidden("You cannot schedule classes for this batch")
    get_tenant_obj(db, p, Subject, body.subject_id, label="Subject")
    get_tenant_obj(db, p, Teacher, body.teacher_id, label="Teacher")
    if body.end_time <= body.start_time:
        raise ValidationFailed("End time must be after start time")
    if body.makeup_for_session_id:
        orig = get_tenant_obj(db, p, ClassSession, body.makeup_for_session_id, label="Original session")
        if orig.status not in ("cancelled", "postponed", "teacher_absent"):
            raise ValidationFailed("Makeup classes can only replace cancelled, postponed or teacher-absent sessions")
    tz = scheduling.institute_tz(db, p.institute_id)
    st = scheduling.local_to_utc(body.session_date, body.start_time, tz)
    en = scheduling.local_to_utc(body.session_date, body.end_time, tz)
    room = body.classroom_id or batch.default_classroom_id
    conflicts = scheduling.session_conflicts(db, p.institute_id, st, en, {body.teacher_id}, batch.id, room)
    scheduling.enforce_no_conflict(conflicts, body.override_reason, p.can("schedules.override_conflict"))
    s = ClassSession(institute_id=p.institute_id, branch_id=batch.branch_id, academic_year_id=batch.academic_year_id, batch_id=batch.id,
                     subject_id=body.subject_id, scheduled_teacher_id=body.teacher_id, classroom_id=room, session_date=body.session_date,
                     scheduled_start=st, scheduled_end=en, status="scheduled", session_type=body.session_type,
                     makeup_for_session_id=body.makeup_for_session_id, online_meeting_url=body.online_meeting_url, remarks=body.remarks,
                     conflict_override_reason=body.override_reason if conflicts else None, created_by_id=p.user_id, updated_by_id=p.user_id)
    db.add(s)
    db.flush()
    db.add(ClassSessionTeacher(institute_id=p.institute_id, session_id=s.id, teacher_id=body.teacher_id, role="scheduled", created_by_id=p.user_id))
    audit.record(db, p, "class_sessions", s.id, "create", new=audit.snapshot(s),
                 reason=body.override_reason if conflicts else None, branch_id=s.branch_id)
    if conflicts:
        audit.record(db, p, "class_sessions", s.id, "conflict_override", new={"conflicts": conflicts}, reason=body.override_reason)
    outbox.emit(db, p.institute_id, "session.scheduled", "class_session", s.id, {"type": body.session_type})
    db.commit()
    return {"id": s.id}


class RescheduleIn(BaseModel):
    new_date: date
    start_time: str = Field(pattern=HHMM)
    end_time: str = Field(pattern=HHMM)
    classroom_id: uuid.UUID | None = None
    reason: str = Field(min_length=3, max_length=1000)
    override_reason: str | None = Field(default=None, max_length=1000)


@router.post("/class-sessions/{sid}/reschedule")
def reschedule(sid: uuid.UUID, body: RescheduleIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("sessions.write"))):
    s = _session(db, p, sid, write=True, lock=True)
    if s.status not in ("scheduled", "postponed"):
        raise Conflict("Only scheduled sessions can be rescheduled")
    if body.end_time <= body.start_time:
        raise ValidationFailed("End time must be after start time")
    tz = scheduling.institute_tz(db, p.institute_id)
    st, en = scheduling.local_to_utc(body.new_date, body.start_time, tz), scheduling.local_to_utc(body.new_date, body.end_time, tz)
    teachers = set(db.scalars(select(ClassSessionTeacher.teacher_id).where(ClassSessionTeacher.session_id == s.id)).all()) | {s.scheduled_teacher_id}
    room = body.classroom_id or s.classroom_id
    conflicts = scheduling.session_conflicts(db, p.institute_id, st, en, teachers, s.batch_id, room, exclude_id=s.id)
    scheduling.enforce_no_conflict(conflicts, body.override_reason, p.can("schedules.override_conflict"))
    s.status = "postponed"
    s.remarks = f"Rescheduled: {body.reason}"
    new = ClassSession(institute_id=s.institute_id, branch_id=s.branch_id, schedule_id=None, academic_year_id=s.academic_year_id,
                       batch_id=s.batch_id, subject_id=s.subject_id, scheduled_teacher_id=s.scheduled_teacher_id, classroom_id=room,
                       session_date=body.new_date, scheduled_start=st, scheduled_end=en, status="scheduled", session_type="makeup",
                       rescheduled_from_session_id=s.id, makeup_for_session_id=s.id, online_meeting_url=s.online_meeting_url,
                       remarks=body.reason, conflict_override_reason=body.override_reason if conflicts else None,
                       created_by_id=p.user_id, updated_by_id=p.user_id)
    db.add(new)
    db.flush()
    for tid in teachers:
        role = "scheduled" if tid == s.scheduled_teacher_id else "substitute"
        db.add(ClassSessionTeacher(institute_id=p.institute_id, session_id=new.id, teacher_id=tid, role=role))
    audit.record(db, p, "class_sessions", s.id, "reschedule", new={"new_session_id": new.id, "date": body.new_date}, reason=body.reason)
    outbox.emit(db, p.institute_id, "session.rescheduled", "class_session", s.id,
                {"new_session_id": new.id, "reason": body.reason}, dedupe_key=f"session.rescheduled:{s.id}:{new.id}")
    db.commit()
    return {"new_session_id": new.id}


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


@router.post("/class-sessions/{sid}/cancel")
def cancel(sid: uuid.UUID, body: ReasonIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("sessions.write"))):
    s = _session(db, p, sid, write=True, lock=True)
    if s.status in ("completed", "cancelled"):
        raise Conflict(f"Session is already {s.status}")
    if s.attendance_state == "submitted":
        raise Conflict("Attendance has been submitted for this session; reopen attendance first")
    s.status = "cancelled"
    s.cancellation_reason = body.reason
    s.updated_by_id = p.user_id
    audit.record(db, p, "class_sessions", s.id, "cancel", reason=body.reason, branch_id=s.branch_id)
    outbox.emit(db, p.institute_id, "session.cancelled", "class_session", s.id, {"reason": body.reason}, dedupe_key=f"session.cancelled:{s.id}")
    db.commit()
    return {"ok": True}


class SubstituteIn(BaseModel):
    teacher_id: uuid.UUID
    reason: str = Field(min_length=3, max_length=1000)
    override_reason: str | None = Field(default=None, max_length=1000)


@router.post("/class-sessions/{sid}/substitute")
def substitute(sid: uuid.UUID, body: SubstituteIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("sessions.write"))):
    s = _session(db, p, sid, write=True, lock=True)
    if s.status in ("completed", "cancelled"):
        raise Conflict("Cannot assign a substitute to a completed or cancelled session")
    t = get_tenant_obj(db, p, Teacher, body.teacher_id, label="Teacher")
    if t.id == s.scheduled_teacher_id:
        raise ValidationFailed("Substitute must differ from the scheduled teacher")
    conflicts = scheduling.session_conflicts(db, p.institute_id, s.scheduled_start, s.scheduled_end, {t.id}, None, None, exclude_id=s.id)
    scheduling.enforce_no_conflict(conflicts, body.override_reason, p.can("schedules.override_conflict"))
    existing = db.scalar(select(ClassSessionTeacher).where(ClassSessionTeacher.session_id == s.id, ClassSessionTeacher.teacher_id == t.id))
    if existing:
        raise Conflict("Teacher is already assigned to this session")
    db.add(ClassSessionTeacher(institute_id=p.institute_id, session_id=s.id, teacher_id=t.id, role="substitute", reason=body.reason,
                               created_by_id=p.user_id))
    audit.record(db, p, "class_sessions", s.id, "substitute_assigned", new={"teacher_id": t.id}, reason=body.reason, branch_id=s.branch_id)
    notifications.notify(db, p.institute_id, [t.user_id], "class_rescheduled", "Substitute class assigned",
                         f"You are substituting a class on {s.session_date:%d-%m-%Y}.", link=f"/sessions/{s.id}",
                         dedupe_key=f"sub:{s.id}:{t.id}")
    db.commit()
    return {"ok": True}


@router.post("/class-sessions/{sid}/remove-substitute/{teacher_id}")
def remove_substitute(sid: uuid.UUID, teacher_id: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("sessions.write"))):
    s = _session(db, p, sid, write=True, lock=True)
    if s.status == "completed":
        raise Conflict("Completed sessions keep their teacher history")
    row = db.scalar(select(ClassSessionTeacher).where(ClassSessionTeacher.session_id == s.id, ClassSessionTeacher.teacher_id == teacher_id,
                                                      ClassSessionTeacher.role == "substitute"))
    if not row:
        raise ValidationFailed("Substitute not found")
    if db.scalar(select(TeacherAttendance.id).where(TeacherAttendance.session_id == s.id, TeacherAttendance.teacher_id == teacher_id)):
        raise Conflict("Attendance is recorded for this substitute; it cannot be removed")
    db.delete(row)
    audit.record(db, p, "class_sessions", s.id, "substitute_removed", old={"teacher_id": teacher_id})
    db.commit()
    return {"ok": True}


@router.post("/class-sessions/{sid}/start")
def start_session(sid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    s = _session(db, p, sid, write=True, lock=True)
    if s.status != "scheduled":
        raise Conflict("Only scheduled sessions can be started")
    s.status = "in_progress"
    s.actual_start = datetime.now(timezone.utc)
    audit.record(db, p, "class_sessions", s.id, "start", branch_id=s.branch_id)
    db.commit()
    return {"ok": True}


class CompleteIn(BaseModel):
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    topic_covered: str | None = Field(default=None, max_length=5000)
    syllabus_chapter_id: uuid.UUID | None = None
    chapter_completed: bool = False
    remarks: str | None = Field(default=None, max_length=2000)


@router.post("/class-sessions/{sid}/complete")
def complete_session(sid: uuid.UUID, body: CompleteIn, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    s = _session(db, p, sid, write=True, lock=True)
    if not (p.can("sessions.write") or teacher_can_handle_session(db, p, s)):
        raise Forbidden("Only the class teacher or administrators can complete a session")
    if s.status not in ("scheduled", "in_progress", "pending_verification"):
        raise Conflict(f"Session cannot be completed from status '{s.status}'")
    now = datetime.now(timezone.utc)
    s.actual_start = body.actual_start or s.actual_start or s.scheduled_start
    s.actual_end = body.actual_end or (now if s.status == "in_progress" else s.scheduled_end)
    if s.actual_end < s.actual_start:
        raise ValidationFailed("Actual end must be after actual start")
    s.topic_covered = body.topic_covered or s.topic_covered
    s.remarks = body.remarks or s.remarks
    s.status = "completed" if s.attendance_state == "submitted" else "pending_verification"
    s.completed_at = now
    s.updated_by_id = p.user_id
    if body.syllabus_chapter_id:
        ch = get_tenant_obj(db, p, SyllabusChapter, body.syllabus_chapter_id, label="Chapter")
        s.syllabus_chapter_id = ch.id
        prog = db.scalar(select(SyllabusProgress).where(SyllabusProgress.batch_id == s.batch_id, SyllabusProgress.chapter_id == ch.id))
        if prog is None:
            prog = SyllabusProgress(institute_id=p.institute_id, branch_id=s.branch_id, batch_id=s.batch_id, chapter_id=ch.id,
                                    teacher_id=s.scheduled_teacher_id)
            db.add(prog)
        prog.last_session_id = s.id
        prog.status = "completed" if body.chapter_completed else "in_progress"
        if body.chapter_completed:
            prog.completed_date = s.session_date
        lp = db.scalar(select(LessonPlan).where(LessonPlan.batch_id == s.batch_id, LessonPlan.chapter_id == ch.id,
                                                LessonPlan.status.in_(("planned", "in_progress"))).order_by(LessonPlan.planned_date))
        if lp:
            lp.session_id = s.id
            lp.status = "completed" if body.chapter_completed else "in_progress"
            lp.completed_date = s.session_date if body.chapter_completed else None
    audit.record(db, p, "class_sessions", s.id, "complete", new={"status": s.status, "topic": s.topic_covered}, branch_id=s.branch_id)
    if s.status == "completed":
        outbox.emit(db, p.institute_id, "session.completed", "class_session", s.id, {}, dedupe_key=f"session.completed:{s.id}")
    db.commit()
    return {"status": s.status}


@router.post("/class-sessions/{sid}/teacher-absent")
def teacher_absent(sid: uuid.UUID, body: ReasonIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("sessions.write"))):
    s = _session(db, p, sid, write=True, lock=True)
    if s.status in ("completed", "cancelled"):
        raise Conflict(f"Session is already {s.status}")
    s.status = "teacher_absent"
    s.remarks = body.reason
    ta = db.scalar(select(TeacherAttendance).where(TeacherAttendance.session_id == s.id, TeacherAttendance.teacher_id == s.scheduled_teacher_id))
    if ta is None:
        ta = TeacherAttendance(institute_id=p.institute_id, session_id=s.id, teacher_id=s.scheduled_teacher_id, role="scheduled")
        db.add(ta)
    ta.status = "absent"
    ta.absence_reason = body.reason
    ta.marked_by_id = p.user_id
    ta.marked_at = datetime.now(timezone.utc)
    db.add(AttendanceAuditLog(institute_id=p.institute_id, session_id=s.id, teacher_id=s.scheduled_teacher_id, action="teacher_absent",
                              new_status="absent", reason=body.reason, actor_id=p.user_id))
    audit.record(db, p, "class_sessions", s.id, "teacher_absent", reason=body.reason, branch_id=s.branch_id)
    outbox.emit(db, p.institute_id, "teacher.absent", "class_session", s.id, {"reason": body.reason}, dedupe_key=f"teacher.absent:{s.id}")
    db.commit()
    return {"ok": True}


class SessionPatch(BaseModel):
    remarks: str | None = Field(default=None, max_length=2000)
    topic_covered: str | None = Field(default=None, max_length=5000)
    online_meeting_url: str | None = Field(default=None, max_length=500)
    classroom_id: uuid.UUID | None = None


@router.patch("/class-sessions/{sid}")
def patch_session(sid: uuid.UUID, body: SessionPatch, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    s = _session(db, p, sid, write=True, lock=True)
    before = audit.snapshot(s)
    vals = body.model_dump(exclude_unset=True)
    if "classroom_id" in vals and vals["classroom_id"] != s.classroom_id:
        if not p.can("sessions.write"):
            raise Forbidden("Only administrators can change classrooms")
        get_tenant_obj(db, p, Classroom, vals["classroom_id"], label="Classroom")
        c = scheduling.session_conflicts(db, p.institute_id, s.scheduled_start, s.scheduled_end, set(), None, vals["classroom_id"], s.id)
        if c:
            raise Conflict("Classroom is not available", code="schedule_conflict", details=c)
    for k, v in vals.items():
        setattr(s, k, v)
    old, new = audit.diff(before, audit.snapshot(s))
    audit.record(db, p, "class_sessions", s.id, "update", old, new, branch_id=s.branch_id)
    db.commit()
    return {"ok": True}


@router.get("/class-sessions/{sid}/detail")
def session_detail(sid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(get_principal)):
    s = _session(db, p, sid)
    L = _labels(db, [s])
    out = session_out(s, L)
    out["teachers"] = [
        {"teacher_id": t.teacher_id, "name": n, "role": t.role, "reason": t.reason}
        for t, n in db.execute(select(ClassSessionTeacher, Teacher.full_name).join(Teacher, Teacher.id == ClassSessionTeacher.teacher_id)
                               .where(ClassSessionTeacher.session_id == s.id)).all()
    ]
    out["materials"] = [{"id": m.id, "title": m.title, "category": m.category} for m in db.scalars(
        select(Material).where(Material.session_id == s.id, Material.is_archived.is_(False)))]
    out["assignments"] = [{"id": a.id, "title": a.title, "status": a.status, "due_at": a.due_at} for a in db.scalars(
        select(Assignment).where(Assignment.session_id == s.id))]
    out["can_manage"] = p.can("sessions.write") or teacher_can_handle_session(db, p, s)
    out["is_admin"] = p.can("sessions.write")
    return out


# ----------------------------------------------------------------------------- student attendance


def eligible_students(db: Session, s: ClassSession) -> list[tuple[StudentEnrollment, Student]]:
    has_subjects = exists().where(EnrollmentSubject.enrollment_id == StudentEnrollment.id)
    subject_match = exists().where(
        EnrollmentSubject.enrollment_id == StudentEnrollment.id,
        EnrollmentSubject.subject_id == s.subject_id,
        EnrollmentSubject.start_date <= s.session_date,
        or_(EnrollmentSubject.end_date.is_(None), EnrollmentSubject.end_date >= s.session_date),
    )
    return db.execute(
        select(StudentEnrollment, Student)
        .join(Student, Student.id == StudentEnrollment.student_id)
        .where(
            StudentEnrollment.batch_id == s.batch_id,
            StudentEnrollment.start_date <= s.session_date,
            or_(StudentEnrollment.end_date.is_(None), StudentEnrollment.end_date >= s.session_date),
            or_(~has_subjects, subject_match),
        )
        .order_by(Student.full_name)
    ).all()


@router.get("/class-sessions/{sid}/attendance")
def get_attendance(sid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("attendance"))):
    s = _session(db, p, sid)
    records = {r.student_id: r for r in db.scalars(select(StudentAttendance).where(StudentAttendance.session_id == s.id))}
    staffish = p.can("attendance.read") or teacher_can_handle_session(db, p, s)
    roster = []
    for enr, st in eligible_students(db, s):
        if not staffish and st.id not in p.linked_student_ids:
            continue
        r = records.pop(st.id, None)
        roster.append({"student_id": st.id, "student_code": st.student_code, "full_name": st.full_name, "enrollment_id": enr.id,
                       "status": r.status if r else None, "remarks": r.remarks if r else None, "attendance_id": r.id if r else None,
                       "marked_at": r.marked_at if r else None, "is_locked": r.is_locked if r else False})
    for sid_, r in records.items():  # records for students no longer eligible stay visible for history
        if staffish or sid_ in p.linked_student_ids:
            st = db.get(Student, sid_)
            roster.append({"student_id": sid_, "student_code": st.student_code, "full_name": st.full_name, "enrollment_id": r.enrollment_id,
                           "status": r.status, "remarks": r.remarks, "attendance_id": r.id, "marked_at": r.marked_at,
                           "is_locked": r.is_locked, "not_currently_eligible": True})
    return {"session_id": s.id, "attendance_state": s.attendance_state, "session_status": s.status, "records": roster,
            "can_mark": staffish and (p.can("attendance.write") or p.can("attendance.write_own")),
            "can_reopen": p.can("attendance.reopen")}


class AttRecord(BaseModel):
    student_id: uuid.UUID
    status: Literal["present", "absent", "late", "excused", "approved_leave"]
    remarks: str | None = Field(default=None, max_length=500)


class AttIn(BaseModel):
    records: list[AttRecord] = Field(max_length=500)
    submit: bool = False


@router.put("/class-sessions/{sid}/attendance")
def save_attendance(sid: uuid.UUID, body: AttIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("attendance"))):
    s = _session(db, p, sid, write=False, lock=True)
    if not (p.can("attendance.write") or (p.can("attendance.write_own") and teacher_can_handle_session(db, p, s))):
        raise Forbidden("You cannot mark attendance for this session")
    if s.status in ("cancelled", "postponed"):
        raise Conflict("Attendance cannot be marked for a cancelled or postponed session")
    if s.attendance_state == "submitted":
        raise Conflict("Attendance is submitted and locked. Request a correction or ask an administrator to reopen.")
    if s.scheduled_start.date() > (datetime.now(timezone.utc) + timedelta(days=1)).date():
        raise ValidationFailed("Attendance cannot be marked for future sessions")
    eligible = {st.id: enr for enr, st in eligible_students(db, s)}
    seen = set()
    now = datetime.now(timezone.utc)
    existing = {r.student_id: r for r in db.scalars(select(StudentAttendance).where(StudentAttendance.session_id == s.id).with_for_update())}
    for rec in body.records:
        if rec.student_id in seen:
            raise ValidationFailed("Duplicate student in attendance payload")
        seen.add(rec.student_id)
        if rec.student_id not in eligible and rec.student_id not in existing:
            raise ValidationFailed("A student is not eligible for this session")
        row = existing.get(rec.student_id)
        if row is None:
            row = StudentAttendance(institute_id=p.institute_id, session_id=s.id, student_id=rec.student_id,
                                    enrollment_id=eligible[rec.student_id].id if rec.student_id in eligible else None)
            db.add(row)
            old_status = None
        else:
            old_status = row.status
        if old_status != rec.status or row.remarks != rec.remarks:
            row.status = rec.status
            row.remarks = rec.remarks
            row.marked_by_id = p.user_id
            row.marked_at = now
            if s.attendance_state == "reopened" and old_status and old_status != rec.status:
                db.add(AttendanceAuditLog(institute_id=p.institute_id, session_id=s.id, student_id=rec.student_id, action="corrected_after_reopen",
                                          old_status=old_status, new_status=rec.status, actor_id=p.user_id))
    if body.submit:
        missing = set(eligible) - seen - {sid_ for sid_, r in existing.items() if r.status}
        if missing:
            raise ValidationFailed(f"Mark all eligible students before submitting ({len(missing)} unmarked)")
        db.flush()
        for r in db.scalars(select(StudentAttendance).where(StudentAttendance.session_id == s.id)):
            r.is_locked = True
        s.attendance_state = "submitted"
        s.attendance_submitted_at = now
        s.attendance_submitted_by_id = p.user_id
        if s.status == "pending_verification":
            s.status = "completed"
            outbox.emit(db, p.institute_id, "session.completed", "class_session", s.id, {}, dedupe_key=f"session.completed:{s.id}")
        db.add(AttendanceAuditLog(institute_id=p.institute_id, session_id=s.id, action="submitted", actor_id=p.user_id,
                                  new_status=f"{len(seen)} records"))
        outbox.emit(db, p.institute_id, "attendance.submitted", "class_session", s.id, {}, dedupe_key=f"attendance.submitted:{s.id}:{now.timestamp()}")
    else:
        if s.attendance_state == "not_started":
            s.attendance_state = "draft"
    audit.record(db, p, "class_sessions", s.id, "attendance_submit" if body.submit else "attendance_draft",
                 new={"records": len(body.records)}, branch_id=s.branch_id)
    db.commit()
    return {"attendance_state": s.attendance_state, "session_status": s.status}


@router.post("/class-sessions/{sid}/attendance/reopen")
def reopen_attendance(sid: uuid.UUID, body: ReasonIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("attendance.reopen"))):
    s = _session(db, p, sid, lock=True)
    if s.attendance_state != "submitted":
        raise Conflict("Attendance is not submitted")
    s.attendance_state = "reopened"
    for r in db.scalars(select(StudentAttendance).where(StudentAttendance.session_id == s.id)):
        r.is_locked = False
    db.add(AttendanceAuditLog(institute_id=p.institute_id, session_id=s.id, action="reopened", reason=body.reason, actor_id=p.user_id))
    audit.record(db, p, "class_sessions", s.id, "attendance_reopen", reason=body.reason, branch_id=s.branch_id)
    db.commit()
    return {"ok": True}


class CorrectionIn(BaseModel):
    attendance_id: uuid.UUID
    requested_status: Literal["present", "absent", "late", "excused", "approved_leave"]
    reason: str = Field(min_length=3, max_length=1000)


@router.post("/attendance/corrections", status_code=201)
def request_correction(body: CorrectionIn, db: Session = Depends(get_db), p: Principal = Depends(require_feature("attendance"))):
    att = get_tenant_obj(db, p, StudentAttendance, body.attendance_id, label="Attendance record")
    s = get_tenant_obj(db, p, ClassSession, att.session_id)
    if not (p.can("attendance.write") or teacher_can_handle_session(db, p, s)):
        raise Forbidden("Only the class teacher or administrators can request corrections")
    if att.status == body.requested_status:
        raise ValidationFailed("Requested status equals the current status")
    if db.scalar(select(AttendanceCorrection.id).where(AttendanceCorrection.attendance_id == att.id, AttendanceCorrection.status == "pending")):
        raise Conflict("A correction request is already pending for this record")
    c = AttendanceCorrection(institute_id=p.institute_id, attendance_id=att.id, session_id=att.session_id, student_id=att.student_id,
                             original_status=att.status, requested_status=body.requested_status, reason=body.reason, requested_by_id=p.user_id)
    db.add(c)
    db.flush()
    notifications.notify(db, p.institute_id, notifications.staff_user_ids(db, p.institute_id, ("institute_admin", "branch_admin", "academic_coordinator")),
                         "attendance_alert", "Attendance correction requested", body.reason, link="/r/attendance-corrections",
                         dedupe_key=f"corr:{c.id}")
    db.commit()
    return {"id": c.id}


class DecisionIn(BaseModel):
    status: Literal["approved", "rejected"]
    remarks: str | None = Field(default=None, max_length=1000)


@router.post("/attendance/corrections/{cid}/decide")
def decide_correction(cid: uuid.UUID, body: DecisionIn, db: Session = Depends(get_db), p: Principal = Depends(require_perm("attendance.correct_approve"))):
    c = get_tenant_obj(db, p, AttendanceCorrection, cid, lock=True, label="Correction")
    if c.status != "pending":
        raise Conflict("Correction already decided")
    c.status = body.status
    c.reviewed_by_id = p.user_id
    c.reviewed_at = datetime.now(timezone.utc)
    c.review_remarks = body.remarks
    if body.status == "approved":
        att = db.scalar(select(StudentAttendance).where(StudentAttendance.id == c.attendance_id).with_for_update())
        old = att.status
        att.status = c.requested_status
        att.marked_by_id = p.user_id
        att.marked_at = datetime.now(timezone.utc)
        db.add(AttendanceAuditLog(institute_id=p.institute_id, session_id=c.session_id, student_id=c.student_id, action="correction_approved",
                                  old_status=old, new_status=c.requested_status, reason=c.reason, actor_id=p.user_id))
    audit.record(db, p, "attendance_corrections", c.id, f"correction_{body.status}", reason=body.remarks)
    db.commit()
    return {"ok": True}


# ----------------------------------------------------------------------------- teacher attendance


@router.get("/class-sessions/{sid}/teacher-attendance")
def get_teacher_attendance(sid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_feature("attendance"))):
    s = _session(db, p, sid)
    if not (p.can("teacher_attendance.read") or teacher_can_handle_session(db, p, s)):
        raise Forbidden("You cannot view teacher attendance")
    expected = db.execute(select(ClassSessionTeacher.teacher_id, ClassSessionTeacher.role, Teacher.full_name)
                          .join(Teacher, Teacher.id == ClassSessionTeacher.teacher_id).where(ClassSessionTeacher.session_id == s.id)).all()
    if not expected:
        t = db.get(Teacher, s.scheduled_teacher_id)
        expected = [(t.id, "scheduled", t.full_name)]
    rec = {r.teacher_id: r for r in db.scalars(select(TeacherAttendance).where(TeacherAttendance.session_id == s.id))}
    return [{"teacher_id": tid, "name": name, "role": role, **({k: getattr(rec[tid], k) for k in
            ("id", "status", "arrival_at", "departure_at", "teaching_minutes", "absence_reason", "is_verified", "marked_at")} if tid in rec else {})}
            for tid, role, name in expected]


class TARecord(BaseModel):
    teacher_id: uuid.UUID
    status: Literal["present", "absent", "late", "on_leave", "excused"]
    arrival_at: datetime | None = None
    departure_at: datetime | None = None
    absence_reason: str | None = Field(default=None, max_length=1000)

    @field_validator("departure_at")
    @classmethod
    def _order(cls, v, info):
        a = info.data.get("arrival_at")
        if v and a and v < a:
            raise ValueError("Departure must be after arrival")
        return v


@router.put("/class-sessions/{sid}/teacher-attendance")
def save_teacher_attendance(sid: uuid.UUID, records: list[TARecord], db: Session = Depends(get_db), p: Principal = Depends(require_feature("attendance"))):
    s = _session(db, p, sid, lock=True)
    admin = p.can("teacher_attendance.write")
    allowed = set(db.scalars(select(ClassSessionTeacher.teacher_id).where(ClassSessionTeacher.session_id == s.id)).all()) | {s.scheduled_teacher_id}
    now = datetime.now(timezone.utc)
    for rec in records:
        if rec.teacher_id not in allowed:
            raise ValidationFailed("Teacher is not assigned to this session")
        if not admin and not (p.can("teacher_attendance.write_own") and rec.teacher_id == p.teacher_id):
            raise Forbidden("You can only record your own attendance")
        row = db.scalar(select(TeacherAttendance).where(TeacherAttendance.session_id == s.id, TeacherAttendance.teacher_id == rec.teacher_id).with_for_update())
        if row and row.is_verified and not admin:
            raise Conflict("Verified attendance can only be changed by administrators")
        if row is None:
            role = db.scalar(select(ClassSessionTeacher.role).where(ClassSessionTeacher.session_id == s.id, ClassSessionTeacher.teacher_id == rec.teacher_id)) or "scheduled"
            row = TeacherAttendance(institute_id=p.institute_id, session_id=s.id, teacher_id=rec.teacher_id, role=role)
            db.add(row)
        old = row.status
        row.status = rec.status
        row.arrival_at = rec.arrival_at
        row.departure_at = rec.departure_at
        row.absence_reason = rec.absence_reason
        row.teaching_minutes = int((rec.departure_at - rec.arrival_at).total_seconds() // 60) if rec.arrival_at and rec.departure_at else None
        row.marked_by_id = p.user_id
        row.marked_at = now
        if row.is_verified:
            row.is_verified = False
        db.add(AttendanceAuditLog(institute_id=p.institute_id, session_id=s.id, teacher_id=rec.teacher_id, action="teacher_marked",
                                  old_status=old, new_status=rec.status, actor_id=p.user_id))
    audit.record(db, p, "class_sessions", s.id, "teacher_attendance", new={"records": len(records)}, branch_id=s.branch_id)
    db.commit()
    return {"ok": True}


@router.post("/class-sessions/{sid}/teacher-attendance/verify")
def verify_teacher_attendance(sid: uuid.UUID, db: Session = Depends(get_db), p: Principal = Depends(require_perm("teacher_attendance.write"))):
    s = _session(db, p, sid, lock=True)
    rows = db.scalars(select(TeacherAttendance).where(TeacherAttendance.session_id == s.id)).all()
    if not rows:
        raise ValidationFailed("No teacher attendance recorded")
    now = datetime.now(timezone.utc)
    for r in rows:
        if r.status in ("present", "late") and r.teaching_minutes is None:
            r.teaching_minutes = int(((s.actual_end or s.scheduled_end) - (s.actual_start or s.scheduled_start)).total_seconds() // 60)
        r.is_verified = True
        r.verified_by_id = p.user_id
        r.verified_at = now
    audit.record(db, p, "class_sessions", s.id, "teacher_attendance_verified", branch_id=s.branch_id)
    db.commit()
    return {"verified": len(rows)}
