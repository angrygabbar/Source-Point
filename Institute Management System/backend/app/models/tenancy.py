from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.base import (
    ActorMixin,
    Base,
    BranchEntity,
    Entity,
    OptBranchEntity,
    TenantEntity,
    boolean,
    date,
    decimal,
    enum,
    fk,
    integer,
    jsonb,
    string,
    text,
)


class Institute(Entity, Base):
    __tablename__ = "institutes"
    name = string(200, nullable=False)
    code = string(50, nullable=False, index=True)
    legal_name = string(255)
    logo_object_key = string(500, hidden=True)
    primary_color = string(20, default="#1e2a78")
    secondary_color = string(20, default="#2563eb")
    accent_color = string(20, default="#0d9488")
    address = text()
    city = string(120)
    state = string(120)
    postal_code = string(20)
    country = string(2, nullable=False, default="IN")
    phone = string(30)
    email = string(255)
    website = string(255)
    timezone = string(64, nullable=False, default="Asia/Kolkata")
    currency = string(3, nullable=False, default="INR")
    locale = string(16, nullable=False, default="en-IN")
    date_format = string(20, nullable=False, default="DD-MM-YYYY")
    tax_enabled = boolean(False)
    tax_label = string(20, default="GST")
    tax_rate = decimal(5, 2, nullable=False, default=0)
    tax_registration_number = string(30, label="GSTIN / tax registration")
    invoice_prefix = string(10, nullable=False, default="INV")
    receipt_prefix = string(10, nullable=False, default="RCT")
    financial_year_start_month = integer(nullable=False, default=4)
    storage_quota_mb = integer(nullable=False, default=10240)
    is_active = boolean(True)
    custom_fields = jsonb()
    __table_args__ = (UniqueConstraint("code"),)


class Branch(TenantEntity, Base):
    __tablename__ = "branches"
    name = string(200, nullable=False)
    code = string(50, nullable=False)
    address = text()
    city = string(120)
    state = string(120)
    postal_code = string(20)
    phone = string(30)
    email = string(255)
    is_head_office = boolean(False)
    is_active = boolean(True)
    __table_args__ = (UniqueConstraint("institute_id", "code"),)


class AcademicYear(TenantEntity, Base):
    __tablename__ = "academic_years"
    name = string(50, nullable=False)
    start_date = date(nullable=False)
    end_date = date(nullable=False)
    status = enum("planned", "active", "closed", default="planned")
    is_current = boolean(False)
    __table_args__ = (
        UniqueConstraint("institute_id", "name"),
        CheckConstraint("end_date > start_date", name="ck_academic_years_dates"),
    )


class Classroom(BranchEntity, Base):
    __tablename__ = "classrooms"
    name = string(120, nullable=False)
    code = string(50, nullable=False)
    capacity = integer(nullable=False, default=30)
    location = string(255)
    facilities = text()
    is_online = boolean(False)
    is_active = boolean(True)
    __table_args__ = (
        UniqueConstraint("branch_id", "code"),
        CheckConstraint("capacity >= 0", name="ck_classrooms_capacity"),
    )


class Course(OptBranchEntity, ActorMixin, Base):
    __tablename__ = "courses"
    name = string(200, nullable=False)
    code = string(50, nullable=False)
    description = text()
    duration_months = integer()
    is_active = boolean(True)
    __table_args__ = (UniqueConstraint("institute_id", "code"),)


class Subject(TenantEntity, ActorMixin, Base):
    __tablename__ = "subjects"
    name = string(200, nullable=False)
    code = string(50, nullable=False)
    course_id = fk("courses.id")
    description = text()
    is_active = boolean(True)
    __table_args__ = (UniqueConstraint("institute_id", "code"),)


class Batch(BranchEntity, ActorMixin, Base):
    __tablename__ = "batches"
    name = string(200, nullable=False)
    code = string(50, nullable=False)
    course_id = fk("courses.id", nullable=False)
    academic_year_id = fk("academic_years.id", nullable=False)
    default_classroom_id = fk("classrooms.id")
    start_date = date(nullable=False)
    end_date = date()
    capacity = integer(nullable=False, default=30)
    status = enum("planned", "active", "completed", "archived", default="active")
    description = text()
    __table_args__ = (
        UniqueConstraint("institute_id", "code"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_batches_dates"),
        CheckConstraint("capacity >= 0", name="ck_batches_capacity"),
    )


class BatchSubject(TenantEntity, Base):
    __tablename__ = "batch_subjects"
    batch_id = fk("batches.id", nullable=False, ondelete="CASCADE")
    subject_id = fk("subjects.id", nullable=False)
    weekly_hours = decimal(5, 2)
    is_active = boolean(True)
    __table_args__ = (UniqueConstraint("batch_id", "subject_id"),)


class Holiday(OptBranchEntity, Base):
    __tablename__ = "holidays"
    holiday_date = date(nullable=False, index=True)
    name = string(200, nullable=False)
    description = text()
    applies_to_classes = boolean(True)
    __table_args__ = (UniqueConstraint("institute_id", "branch_id", "holiday_date"),)
