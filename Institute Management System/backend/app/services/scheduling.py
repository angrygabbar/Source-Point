import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.models import (
    ClassSchedule,
    ClassScheduleException,
    ClassSession,
    ClassSessionTeacher,
    Holiday,
    Institute,
)

INACTIVE_SESSION = ("cancelled", "postponed")


def institute_tz(db: Session, institute_id: uuid.UUID) -> ZoneInfo:
    inst = db.get(Institute, institute_id)
    try:
        return ZoneInfo(inst.timezone if inst else "Asia/Kolkata")
    except Exception:  # noqa: BLE001
        return ZoneInfo("Asia/Kolkata")


def local_to_utc(d: date, hhmm: str, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, time.fromisoformat(hhmm), tzinfo=tz).astimezone(timezone.utc)


def today_local(db: Session, institute_id: uuid.UUID) -> date:
    return datetime.now(institute_tz(db, institute_id)).date()


def schedule_conflicts(db: Session, sch: ClassSchedule) -> list[str]:
    """Overlapping recurring slots for the same teacher, batch or classroom."""
    far = date(9999, 12, 31)
    q = select(ClassSchedule).where(
        ClassSchedule.institute_id == sch.institute_id,
        ClassSchedule.is_active.is_(True),
        ClassSchedule.day_of_week == sch.day_of_week,
        ClassSchedule.start_time < sch.end_time,
        ClassSchedule.end_time > sch.start_time,
        ClassSchedule.effective_from <= (sch.effective_to or far),
        or_(ClassSchedule.effective_to.is_(None), ClassSchedule.effective_to >= sch.effective_from),
    )
    if sch.id:
        q = q.where(ClassSchedule.id != sch.id)
    found: list[str] = []
    for other in db.scalars(q):
        if other.teacher_id == sch.teacher_id:
            found.append(f"Teacher already scheduled {other.start_time}-{other.end_time}")
        if other.batch_id == sch.batch_id:
            found.append(f"Batch already has a class {other.start_time}-{other.end_time}")
        if sch.classroom_id and other.classroom_id == sch.classroom_id:
            found.append(f"Classroom already booked {other.start_time}-{other.end_time}")
    return found


def session_conflicts(
    db: Session,
    institute_id: uuid.UUID,
    start: datetime,
    end: datetime,
    teacher_ids: set[uuid.UUID],
    batch_id: uuid.UUID | None,
    classroom_id: uuid.UUID | None,
    exclude_id: uuid.UUID | None = None,
) -> list[str]:
    base = and_(
        ClassSession.institute_id == institute_id,
        ClassSession.status.notin_(INACTIVE_SESSION),
        ClassSession.scheduled_start < end,
        ClassSession.scheduled_end > start,
    )
    if exclude_id:
        base = and_(base, ClassSession.id != exclude_id)
    found: list[str] = []
    sub_teacher_sessions = select(ClassSessionTeacher.session_id).where(ClassSessionTeacher.teacher_id.in_(teacher_ids))
    conds = []
    if teacher_ids:
        conds.append(ClassSession.scheduled_teacher_id.in_(teacher_ids))
        conds.append(ClassSession.id.in_(sub_teacher_sessions))
    if batch_id:
        conds.append(ClassSession.batch_id == batch_id)
    if classroom_id:
        conds.append(ClassSession.classroom_id == classroom_id)
    if not conds:
        return found
    for s in db.scalars(select(ClassSession).where(base, or_(*conds)).limit(20)):
        local = s.scheduled_start.isoformat(timespec="minutes")
        if s.batch_id == batch_id:
            found.append(f"Batch has another class at {local}")
        if classroom_id and s.classroom_id == classroom_id:
            found.append(f"Classroom is booked at {local}")
        if s.scheduled_teacher_id in teacher_ids:
            found.append(f"Teacher has another class at {local}")
        elif s.batch_id != batch_id and not (classroom_id and s.classroom_id == classroom_id):
            found.append(f"Teacher is substituting another class at {local}")
    return sorted(set(found))


def enforce_no_conflict(conflicts: list[str], override_reason: str | None, can_override: bool) -> None:
    if not conflicts:
        return
    if override_reason and can_override:
        return
    raise Conflict(
        "Scheduling conflict detected" + ("" if can_override else " (override requires permission)"),
        code="schedule_conflict",
        details=conflicts,
    )


def generate_sessions(
    db: Session,
    institute_id: uuid.UUID,
    start_date: date,
    end_date: date,
    schedule_ids: list[uuid.UUID] | None = None,
    actor_id: uuid.UUID | None = None,
) -> dict[str, int]:
    """Materialise recurring schedules into permanent class-session records (idempotent)."""
    tz = institute_tz(db, institute_id)
    q = select(ClassSchedule).where(
        ClassSchedule.institute_id == institute_id,
        ClassSchedule.is_active.is_(True),
        ClassSchedule.effective_from <= end_date,
        or_(ClassSchedule.effective_to.is_(None), ClassSchedule.effective_to >= start_date),
    )
    if schedule_ids:
        q = q.where(ClassSchedule.id.in_(schedule_ids))
    schedules = db.scalars(q).all()
    holidays = db.execute(
        select(Holiday.holiday_date, Holiday.branch_id).where(
            Holiday.institute_id == institute_id,
            Holiday.applies_to_classes.is_(True),
            Holiday.holiday_date.between(start_date, end_date),
        )
    ).all()
    holiday_set = {(h[0], h[1]) for h in holidays}
    exceptions = {
        (e.schedule_id, e.exception_date): e
        for e in db.scalars(
            select(ClassScheduleException).where(
                ClassScheduleException.institute_id == institute_id,
                ClassScheduleException.exception_date.between(start_date, end_date),
            )
        )
    }
    created = skipped = 0
    for sch in schedules:
        d = max(start_date, sch.effective_from)
        last = min(end_date, sch.effective_to or end_date)
        while d <= last:
            if d.weekday() != sch.day_of_week:
                d += timedelta(days=1)
                continue
            if (d, None) in holiday_set or (d, sch.branch_id) in holiday_set:
                skipped += 1
                d += timedelta(days=7)
                continue
            exc = exceptions.get((sch.id, d))
            session_date, st, et = d, sch.start_time, sch.end_time
            status, reason, classroom = "scheduled", None, sch.classroom_id
            if exc:
                if exc.action == "cancel":
                    status, reason = "cancelled", exc.reason
                elif exc.action == "reschedule":
                    session_date = exc.new_date or d
                    st = exc.new_start_time or st
                    et = exc.new_end_time or et
                    reason = exc.reason
                elif exc.action == "change_room":
                    classroom = exc.new_classroom_id or classroom
                if exc.new_classroom_id:
                    classroom = exc.new_classroom_id
            sid = uuid.uuid4()
            res = db.execute(
                insert(ClassSession)
                .values(
                    id=sid,
                    institute_id=institute_id,
                    branch_id=sch.branch_id,
                    schedule_id=sch.id,
                    academic_year_id=sch.academic_year_id,
                    batch_id=sch.batch_id,
                    subject_id=sch.subject_id,
                    scheduled_teacher_id=sch.teacher_id,
                    classroom_id=classroom,
                    session_date=session_date,
                    scheduled_start=local_to_utc(session_date, st, tz),
                    scheduled_end=local_to_utc(session_date, et, tz),
                    status=status,
                    session_type="regular",
                    cancellation_reason=reason if status == "cancelled" else None,
                    remarks=reason if status != "cancelled" else None,
                    online_meeting_url=sch.online_meeting_url,
                    attendance_state="not_started",
                    billing_processed=False,
                    compensation_processed=False,
                    created_by_id=actor_id,
                )
                .on_conflict_do_nothing(
                    index_elements=["schedule_id", "session_date"],
                    index_where=and_(ClassSession.schedule_id.isnot(None), ClassSession.session_type == "regular"),
                )
                .returning(ClassSession.id)
            ).first()
            if res is None:
                skipped += 1
            else:
                created += 1
                db.add(ClassSessionTeacher(institute_id=institute_id, session_id=sid, teacher_id=sch.teacher_id, role="scheduled"))
                if exc and exc.action == "substitute" and exc.substitute_teacher_id:
                    db.add(
                        ClassSessionTeacher(
                            institute_id=institute_id,
                            session_id=sid,
                            teacher_id=exc.substitute_teacher_id,
                            role="substitute",
                            reason=exc.reason,
                        )
                    )
            d += timedelta(days=7)
    db.flush()
    return {"created": created, "skipped": skipped, "schedules": len(schedules)}
