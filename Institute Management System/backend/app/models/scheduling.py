from sqlalchemy import CheckConstraint, Index, UniqueConstraint, text as sql_text

from app.models.base import (
    ActorMixin,
    Base,
    BranchEntity,
    TenantEntity,
    boolean,
    date,
    enum,
    fk,
    integer,
    string,
    text,
    ts,
)

SESSION_STATUSES = ("scheduled", "in_progress", "completed", "cancelled", "postponed", "teacher_absent", "pending_verification")
STUDENT_ATTENDANCE = ("present", "absent", "late", "excused", "approved_leave")
TEACHER_ATTENDANCE = ("present", "absent", "late", "on_leave", "excused")
_TIME_RE = "'^([01][0-9]|2[0-3]):[0-5][0-9]$'"


class ClassSchedule(BranchEntity, ActorMixin, Base):
    __tablename__ = "class_schedules"
    title = string(200)
    academic_year_id = fk("academic_years.id", nullable=False)
    batch_id = fk("batches.id", nullable=False)
    subject_id = fk("subjects.id", nullable=False)
    teacher_id = fk("teachers.id", nullable=False)
    classroom_id = fk("classrooms.id")
    day_of_week = integer(nullable=False, label="Day of week (0=Mon … 6=Sun)")
    start_time = string(5, nullable=False, widget="time")
    end_time = string(5, nullable=False, widget="time")
    effective_from = date(nullable=False)
    effective_to = date()
    online_meeting_url = string(500)
    is_active = boolean(True)
    conflict_override_reason = text()
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_schedules_dow"),
        CheckConstraint(f"start_time ~ {_TIME_RE} AND end_time ~ {_TIME_RE}", name="ck_schedules_time_format"),
        CheckConstraint("end_time > start_time", name="ck_schedules_times"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_schedules_dates"),
    )


class ClassScheduleException(TenantEntity, ActorMixin, Base):
    __tablename__ = "class_schedule_exceptions"
    schedule_id = fk("class_schedules.id", nullable=False, ondelete="CASCADE")
    exception_date = date(nullable=False)
    action = enum("cancel", "reschedule", "substitute", "change_room", default="cancel")
    new_date = date()
    new_start_time = string(5, widget="time")
    new_end_time = string(5, widget="time")
    substitute_teacher_id = fk("teachers.id")
    new_classroom_id = fk("classrooms.id")
    reason = text(nullable=False)
    __table_args__ = (UniqueConstraint("schedule_id", "exception_date"),)


class ClassSession(BranchEntity, ActorMixin, Base):
    __tablename__ = "class_sessions"
    schedule_id = fk("class_schedules.id")
    academic_year_id = fk("academic_years.id", nullable=False)
    batch_id = fk("batches.id", nullable=False)
    subject_id = fk("subjects.id", nullable=False)
    scheduled_teacher_id = fk("teachers.id", nullable=False)
    classroom_id = fk("classrooms.id")
    session_date = date(nullable=False, index=True)
    scheduled_start = ts(nullable=False, index=True)
    scheduled_end = ts(nullable=False)
    actual_start = ts()
    actual_end = ts()
    status = enum(*SESSION_STATUSES, default="scheduled")
    session_type = enum("regular", "makeup", "extra", "demo", "exam", "doubt_solving", default="regular")
    makeup_for_session_id = fk("class_sessions.id")
    rescheduled_from_session_id = fk("class_sessions.id")
    cancellation_reason = text()
    remarks = text()
    topic_covered = text()
    syllabus_chapter_id = fk("syllabus_chapters.id")
    online_meeting_url = string(500)
    conflict_override_reason = text()
    attendance_state = enum("not_started", "draft", "submitted", "reopened", default="not_started")
    attendance_submitted_at = ts()
    attendance_submitted_by_id = fk("users.id", ondelete="SET NULL")
    completed_at = ts()
    billing_processed = boolean(False)
    compensation_processed = boolean(False)
    __table_args__ = (
        CheckConstraint("scheduled_end > scheduled_start", name="ck_sessions_times"),
        CheckConstraint("actual_end IS NULL OR actual_start IS NULL OR actual_end >= actual_start", name="ck_sessions_actual"),
        Index(
            "uq_sessions_schedule_date",
            "schedule_id",
            "session_date",
            unique=True,
            postgresql_where=sql_text("schedule_id IS NOT NULL AND session_type = 'regular'"),
        ),
        Index("ix_sessions_teacher_time", "scheduled_teacher_id", "scheduled_start"),
        Index("ix_sessions_batch_time", "batch_id", "scheduled_start"),
    )


class ClassSessionTeacher(TenantEntity, ActorMixin, Base):
    __tablename__ = "class_session_teachers"
    session_id = fk("class_sessions.id", nullable=False, ondelete="CASCADE")
    teacher_id = fk("teachers.id", nullable=False)
    role = enum("scheduled", "substitute", "assistant", default="scheduled")
    reason = text()
    __table_args__ = (UniqueConstraint("session_id", "teacher_id"),)


class StudentAttendance(TenantEntity, Base):
    __tablename__ = "student_attendance"
    session_id = fk("class_sessions.id", nullable=False)
    student_id = fk("students.id", nullable=False)
    enrollment_id = fk("student_enrollments.id")
    status = enum(*STUDENT_ATTENDANCE, default="present")
    remarks = text()
    is_locked = boolean(False)
    marked_by_id = fk("users.id", ondelete="SET NULL")
    marked_at = ts()
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)


class TeacherAttendance(TenantEntity, Base):
    __tablename__ = "teacher_attendance"
    session_id = fk("class_sessions.id", nullable=False)
    teacher_id = fk("teachers.id", nullable=False)
    role = enum("scheduled", "substitute", "assistant", default="scheduled")
    status = enum(*TEACHER_ATTENDANCE, default="present")
    arrival_at = ts()
    departure_at = ts()
    teaching_minutes = integer()
    absence_reason = text()
    leave_id = fk("teacher_leaves.id")
    marked_by_id = fk("users.id", ondelete="SET NULL")
    marked_at = ts()
    is_verified = boolean(False)
    verified_by_id = fk("users.id", ondelete="SET NULL")
    verified_at = ts()
    __table_args__ = (
        UniqueConstraint("session_id", "teacher_id"),
        CheckConstraint("teaching_minutes IS NULL OR teaching_minutes >= 0", name="ck_teacher_att_minutes"),
    )


class AttendanceCorrection(TenantEntity, Base):
    __tablename__ = "attendance_corrections"
    attendance_id = fk("student_attendance.id", nullable=False)
    session_id = fk("class_sessions.id", nullable=False)
    student_id = fk("students.id", nullable=False)
    original_status = enum(*STUDENT_ATTENDANCE)
    requested_status = enum(*STUDENT_ATTENDANCE)
    reason = text(nullable=False)
    status = enum("pending", "approved", "rejected", default="pending")
    requested_by_id = fk("users.id", ondelete="SET NULL")
    reviewed_by_id = fk("users.id", ondelete="SET NULL")
    reviewed_at = ts()
    review_remarks = text()


class AttendanceAuditLog(TenantEntity, Base):
    __tablename__ = "attendance_audit_logs"
    session_id = fk("class_sessions.id", nullable=False)
    student_id = fk("students.id")
    teacher_id = fk("teachers.id")
    action = string(60, nullable=False)
    old_status = string(40)
    new_status = string(40)
    reason = text()
    actor_id = fk("users.id", ondelete="SET NULL")
