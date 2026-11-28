from sqlalchemy import CheckConstraint, UniqueConstraint

from app.models.base import (
    ActorMixin,
    Base,
    BranchEntity,
    TenantEntity,
    date,
    enum,
    fk,
    money,
    string,
    text,
    ts,
)

ENQUIRY_STAGES = ("new", "contacted", "counselling", "demo_class", "admission_offered", "enrolled", "lost")
LEAD_SOURCES = ("walk_in", "website", "phone", "referral", "social_media", "advertisement", "event", "other")


class Campaign(TenantEntity, ActorMixin, Base):
    __tablename__ = "campaigns"
    name = string(200, nullable=False)
    channel = enum(*LEAD_SOURCES, default="advertisement")
    start_date = date()
    end_date = date()
    budget = money(nullable=True, default=None)
    notes = text()


class Lead(BranchEntity, ActorMixin, Base):
    __tablename__ = "leads"
    full_name = string(200, nullable=False)
    phone = string(30, index=True)
    email = string(255)
    guardian_name = string(200)
    guardian_phone = string(30)
    source = enum(*LEAD_SOURCES, default="walk_in")
    campaign_id = fk("campaigns.id")
    referred_by_student_id = fk("students.id")
    referral_name = string(200)
    assigned_to_id = fk("users.id", ondelete="SET NULL")
    notes = text()
    student_id = fk("students.id", label="Converted student")


class Enquiry(BranchEntity, ActorMixin, Base):
    __tablename__ = "enquiries"
    lead_id = fk("leads.id", nullable=False)
    contact_name = string(200, label="Contact name (from lead)")
    course_id = fk("courses.id")
    preferred_batch_id = fk("batches.id")
    interested_subjects = string(500)
    enquiry_mode = enum("walk_in", "online", "phone", "email", default="walk_in")
    stage = enum(*ENQUIRY_STAGES, default="new")
    lost_reason = text()
    expected_join_date = date()
    assigned_to_id = fk("users.id", ondelete="SET NULL")
    counselling_notes = text(sensitive="admissions.counselling")
    last_contacted_at = ts()
    next_follow_up_at = ts(index=True)
    converted_at = ts()
    student_id = fk("students.id")


class FollowUp(TenantEntity, ActorMixin, Base):
    __tablename__ = "follow_ups"
    enquiry_id = fk("enquiries.id", nullable=False)
    due_at = ts(nullable=False, index=True)
    mode = enum("call", "sms", "whatsapp", "email", "visit", "meeting", default="call")
    status = enum("pending", "done", "missed", "cancelled", default="pending")
    notes = text()
    outcome = text()
    assigned_to_id = fk("users.id", ondelete="SET NULL")
    completed_at = ts()
    reminder_sent_at = ts()


class DemoClass(TenantEntity, ActorMixin, Base):
    __tablename__ = "demo_classes"
    enquiry_id = fk("enquiries.id", nullable=False)
    session_id = fk("class_sessions.id")
    scheduled_at = ts(nullable=False)
    teacher_id = fk("teachers.id")
    subject_id = fk("subjects.id")
    status = enum("scheduled", "attended", "no_show", "cancelled", default="scheduled")
    feedback = text()


class AdmissionRecord(BranchEntity, ActorMixin, Base):
    __tablename__ = "admission_records"
    enquiry_id = fk("enquiries.id")
    student_id = fk("students.id")
    offer_date = date(nullable=False)
    offered_batch_id = fk("batches.id")
    offered_fee_plan_id = fk("fee_plans.id")
    offer_amount = money(nullable=True, default=None)
    admission_fee = money(nullable=True, default=None)
    offer_valid_until = date()
    status = enum("offered", "accepted", "declined", "expired", "admitted", default="offered")
    admission_fee_invoice_id = fk("invoices.id")
    admitted_at = ts()
    remarks = text()
    __table_args__ = (
        UniqueConstraint("enquiry_id"),
        CheckConstraint("offer_valid_until IS NULL OR offer_valid_until >= offer_date", name="ck_admission_offer_dates"),
    )
