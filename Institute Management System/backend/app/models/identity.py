from sqlalchemy import CheckConstraint, Index, UniqueConstraint, text as sql_text

from app.models.base import (
    ActorMixin,
    ArchiveMixin,
    Base,
    BranchEntity,
    Entity,
    TenantEntity,
    boolean,
    date,
    enum,
    fk,
    integer,
    jsonb,
    money,
    string,
    text,
    ts,
    uuid_col,
)


class User(Entity, Base):
    __tablename__ = "users"
    institute_id = fk("institutes.id", nullable=True)
    email = string(255, nullable=False)
    phone = string(30)
    full_name = string(200, nullable=False)
    password_hash = string(255, hidden=True)
    is_active = boolean(True)
    is_superuser = boolean(False)
    must_change_password = boolean(False)
    last_login_at = ts()
    password_changed_at = ts()
    failed_login_count = integer(nullable=False, default=0)
    locked_until = ts()
    avatar_object_key = string(500, hidden=True)
    default_branch_id = fk("branches.id")
    closure_requested_at = ts()
    __table_args__ = (Index("uq_users_email_lower", sql_text("lower(email)"), unique=True),)


class Role(Entity, Base):
    __tablename__ = "roles"
    institute_id = fk("institutes.id", nullable=True)
    code = string(60, nullable=False)
    name = string(120, nullable=False)
    description = text()
    is_system = boolean(False)
    portal = enum("admin", "teacher", "student", "parent", default="admin")
    __table_args__ = (
        Index("uq_roles_system_code", "code", unique=True, postgresql_where=sql_text("institute_id IS NULL")),
        Index("uq_roles_institute_code", "institute_id", "code", unique=True, postgresql_where=sql_text("institute_id IS NOT NULL")),
    )


class Permission(Entity, Base):
    __tablename__ = "permissions"
    code = string(100, nullable=False)
    module = string(60, nullable=False)
    description = string(255)
    is_sensitive = boolean(False)
    __table_args__ = (UniqueConstraint("code"),)


class RolePermission(Entity, Base):
    __tablename__ = "role_permissions"
    role_id = fk("roles.id", nullable=False, ondelete="CASCADE")
    permission_id = fk("permissions.id", nullable=False, ondelete="CASCADE")
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)


class UserRole(Entity, Base):
    __tablename__ = "user_roles"
    user_id = fk("users.id", nullable=False, ondelete="CASCADE")
    role_id = fk("roles.id", nullable=False, ondelete="CASCADE")
    branch_id = fk("branches.id", ondelete="CASCADE")
    __table_args__ = (
        Index("uq_user_roles_scope", "user_id", "role_id", sql_text("coalesce(branch_id, '00000000-0000-0000-0000-000000000000'::uuid)"), unique=True),
    )


class RefreshToken(Entity, Base):
    __tablename__ = "refresh_tokens"
    user_id = fk("users.id", nullable=False, ondelete="CASCADE")
    token_hash = string(128, nullable=False)
    family_id = string(64, nullable=False, index=True)
    expires_at = ts(nullable=False)
    revoked_at = ts()
    revoked_reason = string(60)
    replaced_by_id = uuid_col()
    user_agent = string(500)
    ip_address = string(64)
    last_used_at = ts()
    __table_args__ = (UniqueConstraint("token_hash"),)


class LoginHistory(Entity, Base):
    __tablename__ = "login_history"
    user_id = fk("users.id", ondelete="SET NULL")
    institute_id = fk("institutes.id")
    email = string(255)
    success = boolean(False)
    reason = string(120)
    ip_address = string(64)
    user_agent = string(500)


class PasswordResetToken(Entity, Base):
    __tablename__ = "password_reset_tokens"
    user_id = fk("users.id", nullable=False, ondelete="CASCADE")
    token_hash = string(128, nullable=False)
    expires_at = ts(nullable=False)
    used_at = ts()
    created_by_id = fk("users.id", ondelete="SET NULL")
    __table_args__ = (UniqueConstraint("token_hash"),)


class Student(BranchEntity, ActorMixin, ArchiveMixin, Base):
    __tablename__ = "students"
    user_id = fk("users.id", ondelete="SET NULL")
    student_code = string(50, nullable=False)
    full_name = string(200, nullable=False)
    photo_object_key = string(500, hidden=True)
    date_of_birth = date()
    gender = enum("male", "female", "other", "prefer_not_to_say", nullable=True)
    phone = string(30)
    email = string(255)
    address = text()
    city = string(120)
    state = string(120)
    postal_code = string(20)
    school_name = string(200)
    admission_date = date(nullable=False)
    status = enum("active", "inactive", "withdrawn", "alumni", "archived", default="active")
    guardian_name = string(200)
    guardian_phone = string(30)
    guardian_email = string(255)
    guardian_relation = string(50)
    emergency_contact_name = string(200)
    emergency_contact_phone = string(30)
    blood_group = string(5)
    withdrawal_date = date()
    withdrawal_reason = text()
    internal_remarks = text(sensitive="students.sensitive")
    custom_fields = jsonb()
    __table_args__ = (UniqueConstraint("institute_id", "student_code"),)


class Teacher(BranchEntity, ActorMixin, ArchiveMixin, Base):
    __tablename__ = "teachers"
    user_id = fk("users.id", ondelete="SET NULL")
    teacher_code = string(50, nullable=False)
    full_name = string(200, nullable=False)
    photo_object_key = string(500, hidden=True)
    phone = string(30, sensitive="teachers.contact")
    email = string(255, sensitive="teachers.contact")
    address = text(sensitive="teachers.contact")
    gender = enum("male", "female", "other", "prefer_not_to_say", nullable=True)
    date_of_birth = date()
    qualifications = text()
    specialization = string(255)
    joining_date = date(nullable=False)
    exit_date = date()
    exit_reason = text()
    employment_status = enum("active", "on_leave", "notice_period", "resigned", "terminated", default="active")
    employment_type = enum("full_time", "part_time", "visiting", "contract", default="full_time")
    compensation_type = enum("fixed_monthly", "per_class", "per_hour", "custom", default="fixed_monthly")
    compensation_amount = money(sensitive="payroll.read")
    payout_reference = string(255, sensitive="payroll.read", label="Payout reference (no passwords)")
    custom_fields = jsonb()
    __table_args__ = (UniqueConstraint("institute_id", "teacher_code"),)


class Parent(TenantEntity, ActorMixin, Base):
    __tablename__ = "parents"
    user_id = fk("users.id", ondelete="SET NULL")
    full_name = string(200, nullable=False)
    phone = string(30)
    email = string(255)
    occupation = string(120)
    address = text()
    is_active = boolean(True)


class StudentParent(TenantEntity, Base):
    __tablename__ = "student_parents"
    student_id = fk("students.id", nullable=False, ondelete="CASCADE")
    parent_id = fk("parents.id", nullable=False, ondelete="CASCADE")
    relation = enum("father", "mother", "guardian", "other", default="guardian")
    is_primary = boolean(False)
    can_view_fees = boolean(True)
    can_view_academics = boolean(True)
    __table_args__ = (UniqueConstraint("student_id", "parent_id"),)


class StudentEnrollment(BranchEntity, ActorMixin, Base):
    __tablename__ = "student_enrollments"
    student_id = fk("students.id", nullable=False)
    batch_id = fk("batches.id", nullable=False)
    course_id = fk("courses.id", nullable=False)
    academic_year_id = fk("academic_years.id", nullable=False)
    start_date = date(nullable=False)
    end_date = date()
    status = enum("active", "completed", "transferred", "withdrawn", "promoted", default="active")
    transferred_from_id = fk("student_enrollments.id")
    remarks = text()
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_enrollments_dates"),
        Index("uq_enrollment_active", "student_id", "batch_id", unique=True, postgresql_where=sql_text("status = 'active'")),
    )


class EnrollmentSubject(TenantEntity, Base):
    __tablename__ = "enrollment_subjects"
    enrollment_id = fk("student_enrollments.id", nullable=False, ondelete="CASCADE")
    subject_id = fk("subjects.id", nullable=False)
    start_date = date(nullable=False)
    end_date = date()
    __table_args__ = (
        UniqueConstraint("enrollment_id", "subject_id", "start_date"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_enrollment_subjects_dates"),
    )


class TeacherAssignment(BranchEntity, ActorMixin, Base):
    __tablename__ = "teacher_assignments"
    teacher_id = fk("teachers.id", nullable=False)
    batch_id = fk("batches.id", nullable=False)
    subject_id = fk("subjects.id", nullable=False)
    role = enum("primary", "assistant", "substitute", default="primary")
    start_date = date(nullable=False)
    end_date = date()
    is_active = boolean(True)
    __table_args__ = (CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_teacher_assignments_dates"),)


class TeacherAvailability(TenantEntity, Base):
    __tablename__ = "teacher_availability"
    teacher_id = fk("teachers.id", nullable=False, ondelete="CASCADE")
    day_of_week = integer(nullable=False, label="Day of week (0=Mon)")
    start_time = string(5, nullable=False, widget="time")
    end_time = string(5, nullable=False, widget="time")
    effective_from = date()
    effective_to = date()
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_availability_dow"),
        CheckConstraint("end_time > start_time", name="ck_availability_times"),
    )


class TeacherLeave(BranchEntity, ActorMixin, Base):
    __tablename__ = "teacher_leaves"
    teacher_id = fk("teachers.id", nullable=False)
    leave_type = enum("casual", "sick", "earned", "unpaid", "maternity", "other", default="casual")
    start_date = date(nullable=False)
    end_date = date(nullable=False)
    days = integer(nullable=False, default=1)
    reason = text()
    status = enum("pending", "approved", "rejected", "cancelled", default="pending")
    decided_by_id = fk("users.id", ondelete="SET NULL")
    decided_at = ts()
    decision_remarks = text()
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_teacher_leaves_dates"),)


class LeaveBalance(TenantEntity, Base):
    __tablename__ = "leave_balances"
    teacher_id = fk("teachers.id", nullable=False, ondelete="CASCADE")
    year = integer(nullable=False)
    leave_type = enum("casual", "sick", "earned", "unpaid", "maternity", "other", default="casual")
    allotted = integer(nullable=False, default=0)
    used = integer(nullable=False, default=0)
    __table_args__ = (UniqueConstraint("teacher_id", "year", "leave_type"),)


class EmploymentRecord(TenantEntity, ActorMixin, Base):
    __tablename__ = "employment_records"
    teacher_id = fk("teachers.id", nullable=False)
    event_type = enum("joining", "confirmation", "salary_revision", "promotion", "transfer", "warning", "exit", "rejoining", default="joining")
    effective_date = date(nullable=False)
    compensation_type = enum("fixed_monthly", "per_class", "per_hour", "custom", nullable=True)
    compensation_amount = money(nullable=True, default=None, sensitive="payroll.read")
    details = text()


class PerformanceReview(TenantEntity, ActorMixin, Base):
    __tablename__ = "performance_reviews"
    teacher_id = fk("teachers.id", nullable=False)
    period_start = date(nullable=False)
    period_end = date(nullable=False)
    reviewer_id = fk("users.id", ondelete="SET NULL")
    rating = integer(label="Rating (1-5)")
    strengths = text()
    improvements = text()
    comments = text()
    status = enum("draft", "submitted", "acknowledged", default="draft")
    __table_args__ = (CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="ck_reviews_rating"),)


class CounsellingRecord(BranchEntity, ActorMixin, Base):
    __tablename__ = "counselling_records"
    student_id = fk("students.id", nullable=False)
    record_type = enum("counselling", "disciplinary", "academic_guidance", default="counselling")
    record_date = date(nullable=False)
    summary = text(nullable=False)
    action_taken = text()
    follow_up_date = date()
    is_confidential = boolean(True)
