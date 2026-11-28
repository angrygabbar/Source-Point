from sqlalchemy import Index, UniqueConstraint, text as sql_text

from app.models.base import (
    ActorMixin,
    Base,
    Entity,
    TenantEntity,
    boolean,
    decimal,
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


class AuditLog(Entity, Base):
    """Append-only audit trail (UPDATE/DELETE blocked by trigger)."""

    __tablename__ = "audit_logs"
    institute_id = fk("institutes.id")
    branch_id = fk("branches.id")
    actor_id = fk("users.id", ondelete="SET NULL")
    actor_email = string(255)
    entity_type = string(80, nullable=False, index=True)
    entity_id = uuid_col()
    action = string(60, nullable=False)
    old_values = jsonb()
    new_values = jsonb()
    reason = text()
    ip_address = string(64)
    request_id = string(64)
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"), Index("ix_audit_created", "created_at"))


class ApplicationSetting(Entity, Base):
    __tablename__ = "application_settings"
    institute_id = fk("institutes.id")
    key = string(120, nullable=False)
    value = jsonb()
    description = string(255)
    __table_args__ = (UniqueConstraint("institute_id", "key"),)


class FeatureFlag(Entity, Base):
    __tablename__ = "feature_flags"
    institute_id = fk("institutes.id")
    key = string(80, nullable=False)
    enabled = boolean(True)
    description = string(255)
    __table_args__ = (UniqueConstraint("institute_id", "key"),)


class CustomFieldDefinition(TenantEntity, Base):
    __tablename__ = "custom_field_definitions"
    entity_type = enum("student", "teacher", "parent", "lead", default="student")
    field_key = string(60, nullable=False)
    label = string(120, nullable=False)
    field_type = enum("text", "number", "date", "boolean", "select", default="text")
    options = jsonb("list")
    is_required = boolean(False)
    is_active = boolean(True)
    __table_args__ = (UniqueConstraint("institute_id", "entity_type", "field_key"),)


class IntegrationConfig(TenantEntity, ActorMixin, Base):
    __tablename__ = "integration_configs"
    provider_type = enum("email", "sms", "whatsapp", "push", "payment", "ai", "video", default="email")
    provider = string(60, nullable=False)
    is_enabled = boolean(False)
    config = jsonb()
    secrets_encrypted = text(hidden=True)
    last_status = string(60)
    last_error = text()
    last_checked_at = ts()
    monthly_limit = integer()
    __table_args__ = (UniqueConstraint("institute_id", "provider_type", "provider"),)


class ApiKey(TenantEntity, ActorMixin, Base):
    __tablename__ = "api_keys"
    name = string(120, nullable=False)
    key_prefix = string(12, nullable=False)
    key_hash = string(128, nullable=False, hidden=True)
    scopes = jsonb("list")
    last_used_at = ts()
    expires_at = ts()
    revoked_at = ts()
    __table_args__ = (UniqueConstraint("key_hash"),)


class WebhookEndpoint(TenantEntity, ActorMixin, Base):
    __tablename__ = "webhook_endpoints"
    url = string(1000, nullable=False)
    description = string(255)
    events = jsonb("list")
    secret_encrypted = text(hidden=True)
    is_active = boolean(True)


class WebhookDelivery(TenantEntity, Base):
    __tablename__ = "webhook_deliveries"
    endpoint_id = fk("webhook_endpoints.id", nullable=False, ondelete="CASCADE")
    event_type = string(80, nullable=False)
    payload = jsonb()
    status = enum("pending", "delivered", "failed", default="pending")
    attempts = integer(nullable=False, default=0)
    response_status = integer()
    last_error = text()
    next_attempt_at = ts(index=True)
    delivered_at = ts()


class InboundWebhookEvent(Entity, Base):
    __tablename__ = "inbound_webhook_events"
    institute_id = fk("institutes.id")
    provider = string(60, nullable=False)
    event_id = string(255, nullable=False)
    event_type = string(120)
    payload = jsonb()
    signature_valid = boolean(False)
    processed_at = ts()
    error = text()
    __table_args__ = (UniqueConstraint("provider", "event_id"),)


class SubscriptionPlan(Entity, Base):
    __tablename__ = "subscription_plans"
    code = string(40, nullable=False)
    name = string(120, nullable=False)
    description = text()
    price_monthly = money()
    price_annual = money()
    currency = string(3, nullable=False, default="INR")
    max_students = integer()
    max_branches = integer()
    storage_quota_mb = integer()
    modules = jsonb("list")
    trial_days = integer(nullable=False, default=14)
    is_active = boolean(True)
    __table_args__ = (UniqueConstraint("code"),)


class TenantSubscription(TenantEntity, Base):
    __tablename__ = "tenant_subscriptions"
    plan_id = fk("subscription_plans.id", nullable=False)
    status = enum("trial", "active", "past_due", "cancelled", "expired", default="trial")
    billing_cycle = enum("monthly", "annual", default="monthly")
    trial_ends_at = ts()
    current_period_start = ts()
    current_period_end = ts()
    cancelled_at = ts()
    notes = text()


class SaasInvoice(TenantEntity, Base):
    __tablename__ = "saas_invoices"
    subscription_id = fk("tenant_subscriptions.id", nullable=False)
    invoice_number = string(40, nullable=False)
    amount = money()
    currency = string(3, nullable=False, default="INR")
    period_start = ts()
    period_end = ts()
    status = enum("draft", "issued", "paid", "void", default="draft")
    paid_at = ts()
    __table_args__ = (UniqueConstraint("invoice_number"),)


class UsageRecord(TenantEntity, Base):
    __tablename__ = "usage_records"
    metric = enum("storage_bytes", "students", "teachers", "branches", "ai_tokens", "email", "sms", "whatsapp", "push", default="storage_bytes")
    period = string(7, nullable=False, label="YYYY-MM")
    quantity = decimal(18, 2, nullable=False, default=0)
    cost = money()
    __table_args__ = (UniqueConstraint("institute_id", "metric", "period"),)


class BackgroundJob(Entity, Base):
    __tablename__ = "background_jobs"
    institute_id = fk("institutes.id")
    job_type = string(60, nullable=False)
    status = enum("queued", "running", "succeeded", "failed", "cancelled", default="queued")
    params = jsonb()
    result = jsonb()
    result_object_key = string(500, hidden=True)
    result_filename = string(255)
    error = text()
    progress = integer(nullable=False, default=0)
    created_by_id = fk("users.id", ondelete="SET NULL")
    started_at = ts()
    finished_at = ts()


class EventOutbox(Entity, Base):
    __tablename__ = "event_outbox"
    institute_id = fk("institutes.id")
    event_type = string(80, nullable=False)
    aggregate_type = string(60, nullable=False)
    aggregate_id = uuid_col()
    payload = jsonb()
    status = enum("pending", "processing", "processed", "failed", default="pending")
    attempts = integer(nullable=False, default=0)
    available_at = ts(index=True)
    processed_at = ts()
    last_error = text()
    dedupe_key = string(200)
    __table_args__ = (
        Index("ix_outbox_pending", "status", "available_at"),
        Index("uq_outbox_dedupe", "dedupe_key", unique=True, postgresql_where=sql_text("dedupe_key IS NOT NULL")),
    )


class IdempotencyRecord(Entity, Base):
    __tablename__ = "idempotency_records"
    institute_id = fk("institutes.id")
    user_id = fk("users.id", ondelete="SET NULL")
    key = string(120, nullable=False)
    endpoint = string(200, nullable=False)
    status_code = integer(nullable=False, default=200)
    response = jsonb()
    __table_args__ = (UniqueConstraint("institute_id", "key", "endpoint"),)


class AiRequest(TenantEntity, Base):
    __tablename__ = "ai_requests"
    user_id = fk("users.id", ondelete="SET NULL")
    feature = enum(
        "question_generation",
        "assignment_draft",
        "material_summary",
        "document_extraction",
        "progress_summary",
        "learning_assistant",
        "knowledge_qa",
        "report_draft",
        default="assignment_draft",
    )
    provider = string(60)
    model = string(120)
    prompt = text()
    output = text()
    status = enum("pending", "completed", "failed", "approved", "rejected", default="pending")
    prompt_tokens = integer(nullable=False, default=0)
    completion_tokens = integer(nullable=False, default=0)
    cost = decimal(12, 6, nullable=False, default=0)
    error = text()
    reviewed_by_id = fk("users.id", ondelete="SET NULL")
    reviewed_at = ts()
