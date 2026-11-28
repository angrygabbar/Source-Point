from sqlalchemy import Index, UniqueConstraint, text as sql_text

from app.models.base import (
    ActorMixin,
    Base,
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
    money,
    string,
    text,
    ts,
)

NOTIFICATION_EVENTS = (
    "admission",
    "student_absence",
    "teacher_absence",
    "class_cancelled",
    "class_rescheduled",
    "material_uploaded",
    "assignment_published",
    "homework_deadline",
    "submission_received",
    "submission_evaluated",
    "fee_due",
    "fee_overdue",
    "payment_received",
    "announcement",
    "leave_decision",
    "follow_up_due",
    "evaluation_pending",
    "syllabus_delay",
    "attendance_alert",
    "message",
    "exam_results",
    "system",
)
CHANNELS = ("in_app", "email", "sms", "whatsapp", "push")


class Announcement(OptBranchEntity, ActorMixin, Base):
    __tablename__ = "announcements"
    title = string(255, nullable=False)
    body = text(nullable=False, widget="textarea")
    audience = enum("all", "staff", "teachers", "students", "parents", "batch", default="all")
    batch_id = fk("batches.id")
    priority = enum("normal", "important", "urgent", default="normal")
    status = enum("draft", "published", "archived", default="draft")
    publish_at = ts()
    expires_at = ts()
    requires_acknowledgement = boolean(False)
    published_at = ts()


class AnnouncementAcknowledgement(TenantEntity, Base):
    __tablename__ = "announcement_acknowledgements"
    announcement_id = fk("announcements.id", nullable=False, ondelete="CASCADE")
    user_id = fk("users.id", nullable=False, ondelete="CASCADE")
    __table_args__ = (UniqueConstraint("announcement_id", "user_id"),)


class MessageThread(TenantEntity, Base):
    __tablename__ = "message_threads"
    subject = string(255, nullable=False)
    thread_type = enum("direct", "group", "parent_teacher", "assignment", default="direct")
    created_by_id = fk("users.id", ondelete="SET NULL")
    related_student_id = fk("students.id")
    assignment_id = fk("assignments.id")
    is_locked = boolean(False)
    last_message_at = ts(index=True)


class MessageThreadParticipant(TenantEntity, Base):
    __tablename__ = "message_thread_participants"
    thread_id = fk("message_threads.id", nullable=False, ondelete="CASCADE")
    user_id = fk("users.id", nullable=False, ondelete="CASCADE")
    last_read_at = ts()
    __table_args__ = (UniqueConstraint("thread_id", "user_id"),)


class Message(TenantEntity, Base):
    __tablename__ = "messages"
    thread_id = fk("message_threads.id", nullable=False)
    sender_id = fk("users.id", ondelete="SET NULL")
    body = text(nullable=False)
    is_hidden = boolean(False)
    reported = boolean(False)
    report_reason = text()
    reported_by_id = fk("users.id", ondelete="SET NULL")
    moderated_by_id = fk("users.id", ondelete="SET NULL")


class ParentMeeting(TenantEntity, ActorMixin, Base):
    __tablename__ = "parent_meetings"
    parent_id = fk("parents.id", nullable=False)
    teacher_id = fk("teachers.id")
    student_id = fk("students.id", nullable=False)
    scheduled_at = ts(nullable=False)
    duration_minutes = integer(nullable=False, default=30)
    mode = enum("in_person", "online", "phone", default="in_person")
    meeting_url = string(500)
    status = enum("requested", "scheduled", "completed", "cancelled", default="requested")
    agenda = text()
    minutes = text(label="Meeting record / minutes")


class Survey(OptBranchEntity, ActorMixin, Base):
    __tablename__ = "surveys"
    title = string(255, nullable=False)
    description = text()
    survey_type = enum("feedback", "survey", "poll", default="feedback")
    audience = enum("all", "students", "parents", "teachers", "batch", default="students")
    batch_id = fk("batches.id")
    questions = jsonb("list", label='Questions JSON: [{"key":"q1","label":"...","type":"rating|text|choice","options":[]}]')
    is_anonymous = boolean(False)
    status = enum("draft", "open", "closed", default="draft")
    opens_at = ts()
    closes_at = ts()


class SurveyResponse(TenantEntity, Base):
    __tablename__ = "survey_responses"
    survey_id = fk("surveys.id", nullable=False)
    respondent_id = fk("users.id", ondelete="SET NULL")
    respondent_hash = string(64, hidden=True)
    answers = jsonb()
    __table_args__ = (UniqueConstraint("survey_id", "respondent_hash"),)


class ParentConsent(TenantEntity, ActorMixin, Base):
    __tablename__ = "parent_consents"
    parent_id = fk("parents.id", nullable=False)
    student_id = fk("students.id", nullable=False)
    consent_type = enum("data_processing", "photo_media", "communication", "trip", "medical", "other", default="data_processing")
    granted = boolean(True)
    granted_at = ts()
    revoked_at = ts()
    notes = text()


class Notification(Entity, Base):
    __tablename__ = "notifications"
    institute_id = fk("institutes.id")
    user_id = fk("users.id", nullable=False, ondelete="CASCADE")
    event_type = enum(*NOTIFICATION_EVENTS, default="system")
    title = string(255, nullable=False)
    body = text()
    link = string(500)
    data = jsonb()
    is_read = boolean(False)
    read_at = ts()
    dedupe_key = string(200)
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("uq_notifications_dedupe", "user_id", "dedupe_key", unique=True, postgresql_where=sql_text("dedupe_key IS NOT NULL")),
    )


class NotificationPreference(Entity, Base):
    __tablename__ = "notification_preferences"
    user_id = fk("users.id", nullable=False, ondelete="CASCADE")
    event_type = enum(*NOTIFICATION_EVENTS)
    channel = enum(*CHANNELS)
    enabled = boolean(True)
    __table_args__ = (UniqueConstraint("user_id", "event_type", "channel"),)


class NotificationTemplate(Entity, Base):
    __tablename__ = "notification_templates"
    institute_id = fk("institutes.id")
    event_type = enum(*NOTIFICATION_EVENTS)
    channel = enum(*CHANNELS)
    subject = string(255)
    body = text(nullable=False, label="Body (supports {placeholders})")
    provider_template_id = string(120, label="Provider template id (WhatsApp/SMS DLT)")
    is_active = boolean(True)
    __table_args__ = (UniqueConstraint("institute_id", "event_type", "channel"),)


class NotificationDelivery(Entity, Base):
    __tablename__ = "notification_deliveries"
    institute_id = fk("institutes.id")
    notification_id = fk("notifications.id", ondelete="SET NULL")
    user_id = fk("users.id", ondelete="SET NULL")
    channel = enum(*CHANNELS)
    recipient = string(255)
    subject = string(255)
    body = text()
    status = enum("queued", "sending", "sent", "failed", "skipped", "cancelled", default="queued")
    provider = string(60)
    provider_message_id = string(255)
    attempts = integer(nullable=False, default=0)
    max_attempts = integer(nullable=False, default=5)
    last_error = text()
    scheduled_at = ts(index=True)
    next_attempt_at = ts(index=True)
    sent_at = ts()
    dedupe_key = string(200)
    __table_args__ = (Index("uq_deliveries_dedupe", "dedupe_key", unique=True, postgresql_where=sql_text("dedupe_key IS NOT NULL")),)


class PushSubscription(Entity, Base):
    __tablename__ = "push_subscriptions"
    user_id = fk("users.id", nullable=False, ondelete="CASCADE")
    endpoint = string(1000, nullable=False)
    p256dh = string(255, nullable=False)
    auth = string(255, nullable=False)
    user_agent = string(500)
    __table_args__ = (UniqueConstraint("endpoint"),)


# ----------------------------------------------------------------------------- resources


class Book(OptBranchEntity, ActorMixin, Base):
    __tablename__ = "books"
    isbn = string(20)
    title = string(255, nullable=False)
    author = string(255)
    publisher = string(255)
    edition = string(60)
    category = string(120)
    copies_total = integer(nullable=False, default=1)
    copies_available = integer(nullable=False, default=1)
    shelf_location = string(60)
    is_digital = boolean(False)
    digital_url = string(1000)
    material_id = fk("materials.id")
    replacement_cost = money()


class LibraryMember(TenantEntity, ActorMixin, Base):
    __tablename__ = "library_members"
    member_type = enum("student", "teacher", "staff", default="student")
    student_id = fk("students.id")
    teacher_id = fk("teachers.id")
    user_id = fk("users.id", ondelete="SET NULL")
    full_name = string(200, nullable=False)
    membership_number = string(40, nullable=False)
    max_books = integer(nullable=False, default=3)
    valid_until = date()
    is_active = boolean(True)
    __table_args__ = (UniqueConstraint("institute_id", "membership_number"),)


class BookLoan(TenantEntity, ActorMixin, Base):
    __tablename__ = "book_loans"
    book_id = fk("books.id", nullable=False)
    member_id = fk("library_members.id", nullable=False)
    issued_on = date(nullable=False)
    due_date = date(nullable=False)
    returned_on = date()
    status = enum("issued", "returned", "overdue", "lost", "damaged", default="issued")
    fine_amount = money()
    remarks = text()
    reminder_sent_at = ts()


class InventoryItem(OptBranchEntity, ActorMixin, Base):
    __tablename__ = "inventory_items"
    name = string(200, nullable=False)
    sku = string(60)
    category = enum("stationery", "equipment", "consumable", "electronics", "furniture", "other", default="stationery")
    unit = string(20, nullable=False, default="pcs")
    quantity_on_hand = decimal(12, 2, nullable=False, default=0)
    reorder_level = decimal(12, 2, nullable=False, default=0)
    unit_cost = money()
    vendor_id = fk("vendors.id")
    location = string(120)


class InventoryTransaction(TenantEntity, ActorMixin, Base):
    __tablename__ = "inventory_transactions"
    item_id = fk("inventory_items.id", nullable=False)
    txn_type = enum("purchase", "issue", "return", "adjustment", "damage", default="purchase")
    quantity = decimal(12, 2, nullable=False)
    unit_cost = money(nullable=True, default=None)
    txn_date = date(nullable=False)
    reference = string(120)
    issued_to = string(200)
    notes = text()
    purchase_record_id = fk("purchase_records.id")


class Asset(OptBranchEntity, ActorMixin, Base):
    __tablename__ = "assets"
    asset_tag = string(60, nullable=False)
    name = string(200, nullable=False)
    category = enum("projector", "computer", "device", "furniture", "equipment", "vehicle", "other", default="equipment")
    serial_number = string(120)
    purchase_date = date()
    purchase_cost = money(nullable=True, default=None)
    vendor_id = fk("vendors.id")
    classroom_id = fk("classrooms.id")
    status = enum("available", "in_use", "under_maintenance", "retired", "lost", default="available")
    warranty_until = date()
    notes = text()
    __table_args__ = (UniqueConstraint("institute_id", "asset_tag"),)


class AssetAssignment(TenantEntity, ActorMixin, Base):
    __tablename__ = "asset_assignments"
    asset_id = fk("assets.id", nullable=False)
    assigned_to_user_id = fk("users.id", ondelete="SET NULL")
    classroom_id = fk("classrooms.id")
    assigned_on = date(nullable=False)
    returned_on = date()
    notes = text()


class MaintenanceRecord(TenantEntity, ActorMixin, Base):
    __tablename__ = "maintenance_records"
    asset_id = fk("assets.id", nullable=False)
    maintenance_date = date(nullable=False)
    description = text(nullable=False)
    cost = money(nullable=True, default=None)
    vendor_id = fk("vendors.id")
    status = enum("scheduled", "in_progress", "completed", default="scheduled")
    next_due_date = date()
