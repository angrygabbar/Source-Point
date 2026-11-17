"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-04
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)
MONEY = sa.Numeric(12, 2)
EMPTY_JSON = sa.text("'{}'::jsonb")


def _uuid_pk() -> sa.Column:
    return sa.Column("id", pg.UUID(as_uuid=True), primary_key=True)


def _created() -> sa.Column:
    return sa.Column("created_at", TZ, nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS coinback")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("password_changed_at", TZ),
        sa.Column("last_login_at", TZ),
        _created(),
    )

    op.create_table(
        "discovery_sources",
        _uuid_pk(),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("connector_key", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("config", pg.JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("auth_method", sa.String(32), nullable=False, server_default="none"),
        sa.Column("rate_limit_per_minute", sa.Integer, nullable=False, server_default="10"),
        sa.Column("permitted_use_notes", sa.Text),
        sa.Column("last_success_at", TZ),
        sa.Column("last_error", sa.Text),
        sa.Column("last_error_at", TZ),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("backoff_until", TZ),
        _created(),
        sa.Column("updated_at", TZ, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "products",
        _uuid_pk(),
        sa.Column("flipkart_pid", sa.String(64)),
        sa.Column("item_id", sa.String(64)),
        sa.Column("title", sa.Text),
        sa.Column("brand", sa.String(255)),
        sa.Column("category", sa.String(255)),
        sa.Column("product_url", sa.Text, nullable=False),
        sa.Column("normalized_url", sa.Text, nullable=False, unique=True),
        sa.Column("original_url", sa.Text),
        sa.Column("image_url", sa.Text),
        sa.Column("seller", sa.String(255)),
        sa.Column("current_price", MONEY),
        sa.Column("mrp", MONEY),
        sa.Column("discount_percent", sa.Numeric(5, 2)),
        sa.Column("shipping_charge", MONEY),
        sa.Column("in_stock", sa.Boolean),
        sa.Column("variant", sa.String(255)),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("discovery_sources.id", ondelete="SET NULL")),
        sa.Column("submitted_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("access_status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("last_access_error", sa.Text),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("first_seen_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", TZ),
        sa.Column("last_checked_at", TZ),
        sa.Column("archived_at", TZ),
        _created(),
        sa.Column("updated_at", TZ, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_products_flipkart_pid", "products", ["flipkart_pid"], unique=True,
        postgresql_where=sa.text("flipkart_pid IS NOT NULL"),
    )
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_products_brand", "products", ["brand"])
    op.create_index("ix_products_last_checked", "products", ["last_checked_at"])
    op.create_index(
        "ix_products_title_trgm", "products", ["title"],
        postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"},
    )

    op.create_table(
        "offers",
        _uuid_pk(),
        sa.Column("product_id", pg.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("reward_type", sa.String(32), nullable=False),
        sa.Column("is_up_to", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("advertised_coins", sa.Integer),
        sa.Column("advertised_percentage", sa.Numeric(7, 2)),
        sa.Column("per_spend_coins", sa.Integer),
        sa.Column("per_spend_amount", MONEY),
        sa.Column("reward_cap_coins", sa.Integer),
        sa.Column("min_eligible_purchase", MONEY),
        sa.Column("max_eligible_purchase", MONEY),
        sa.Column("eligible_purchase_amount", MONEY),
        sa.Column("estimated_coins", sa.Integer),
        sa.Column("estimated_redemption_value", MONEY),
        sa.Column("actual_redemption_value", MONEY),
        sa.Column("effective_cost_estimate", MONEY),
        sa.Column("status", sa.String(32), nullable=False, server_default="DETECTED"),
        sa.Column("confidence", sa.Numeric(4, 3)),
        sa.Column("classification_reason", sa.Text),
        sa.Column("restrictions", pg.JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("terms", sa.Text),
        sa.Column("valid_from", TZ),
        sa.Column("valid_until", TZ),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("discovery_sources.id", ondelete="SET NULL")),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_url", sa.Text),
        sa.Column("evidence_excerpt", sa.Text),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("first_detected_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("last_changed_at", TZ),
        sa.Column("verified_at", TZ),
        sa.Column("expired_at", TZ),
        _created(),
        sa.Column("updated_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "fingerprint", name="uq_offers_product_fingerprint"),
    )
    op.create_index("ix_offers_advertised_percentage", "offers", ["advertised_percentage"])
    op.create_index("ix_offers_status_valid_until", "offers", ["status", "valid_until"])
    op.create_index("ix_offers_first_detected", "offers", ["first_detected_at"])
    op.create_index("ix_offers_product", "offers", ["product_id"])

    op.create_table(
        "offer_snapshots",
        _uuid_pk(),
        sa.Column("offer_id", pg.UUID(as_uuid=True), sa.ForeignKey("offers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", pg.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reward_coins", sa.Integer),
        sa.Column("estimated_coins", sa.Integer),
        sa.Column("percentage", sa.Numeric(7, 2)),
        sa.Column("cap", sa.Integer),
        sa.Column("selling_price", MONEY),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3)),
        sa.Column("change_type", sa.String(32), nullable=False),
        sa.Column("evidence", pg.JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("captured_at", TZ, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_offer_snapshots_offer_time", "offer_snapshots", ["offer_id", "captured_at"])

    op.create_table(
        "price_history",
        _uuid_pk(),
        sa.Column("product_id", pg.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("selling_price", MONEY),
        sa.Column("mrp", MONEY),
        sa.Column("shipping_charge", MONEY),
        sa.Column("seller", sa.String(255)),
        sa.Column("in_stock", sa.Boolean),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("captured_at", TZ, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_price_history_product_time", "price_history", ["product_id", "captured_at"])

    op.create_table(
        "scan_runs",
        _uuid_pk(),
        sa.Column("trigger", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="QUEUED"),
        sa.Column("source_id", pg.UUID(as_uuid=True), sa.ForeignKey("discovery_sources.id", ondelete="SET NULL")),
        sa.Column("requested_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("queued_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", TZ),
        sa.Column("finished_at", TZ),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("products_discovered", sa.Integer, nullable=False, server_default="0"),
        sa.Column("products_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("offers_detected", sa.Integer, nullable=False, server_default="0"),
        sa.Column("offers_new", sa.Integer, nullable=False, server_default="0"),
        sa.Column("offers_expired", sa.Integer, nullable=False, server_default="0"),
        sa.Column("notifications_queued", sa.Integer, nullable=False, server_default="0"),
        sa.Column("errors_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("progress", pg.JSONB, nullable=False, server_default=EMPTY_JSON),
        sa.Column("details", pg.JSONB, nullable=False, server_default=EMPTY_JSON),
    )
    op.create_index("ix_scan_runs_status", "scan_runs", ["status"])
    op.create_index("ix_scan_runs_started", "scan_runs", ["started_at"])

    op.create_table(
        "notifications",
        _uuid_pk(),
        sa.Column("product_id", pg.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL")),
        sa.Column("offer_id", pg.UUID(as_uuid=True), sa.ForeignKey("offers.id", ondelete="SET NULL")),
        sa.Column("channel", sa.String(32), nullable=False, server_default="telegram"),
        sa.Column("chat_id", sa.String(64)),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("event_key", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("next_attempt_at", TZ),
        sa.Column("last_error", sa.Text),
        sa.Column("sent_at", TZ),
        _created(),
        sa.UniqueConstraint("event_key", name="uq_notifications_event_key"),
    )
    op.create_index("ix_notifications_status_next", "notifications", ["status", "next_attempt_at"])
    op.create_index("ix_notifications_created", "notifications", ["created_at"])

    op.create_table(
        "manual_verifications",
        _uuid_pk(),
        sa.Column("offer_id", pg.UUID(as_uuid=True), sa.ForeignKey("offers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", pg.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("advertised_reward_coins", sa.Integer),
        sa.Column("advertised_percentage", sa.Numeric(7, 2)),
        sa.Column("actual_reward_coins", sa.Integer),
        sa.Column("actual_percentage", sa.Numeric(7, 2)),
        sa.Column("eligible_purchase_amount", MONEY),
        sa.Column("reward_cap_coins", sa.Integer),
        sa.Column("actual_redemption_value", MONEY),
        sa.Column("restrictions", sa.Text),
        sa.Column("expiry", TZ),
        sa.Column("eligibility_notes", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("verified_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("verified_at", TZ, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_manual_verifications_offer", "manual_verifications", ["offer_id", "verified_at"])

    op.create_table(
        "monitored_products",
        _uuid_pk(),
        sa.Column("product_id", pg.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("frequency_minutes", sa.Integer, nullable=False, server_default="15"),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("last_processed_at", TZ),
        sa.Column("next_due_at", TZ),
        _created(),
    )
    op.create_index("ix_monitored_due", "monitored_products", ["enabled", "next_due_at"])

    op.create_table(
        "watchlists",
        _uuid_pk(),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", pg.UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note", sa.Text),
        sa.Column("target_price", MONEY),
        sa.Column("target_percentage", sa.Numeric(7, 2)),
        _created(),
        sa.UniqueConstraint("user_id", "product_id", name="uq_watchlists_user_product"),
    )

    op.create_table(
        "notification_preferences",
        _uuid_pk(),
        sa.Column("scope", sa.String(32), nullable=False, unique=True, server_default="global"),
        sa.Column("channel", sa.String(32), nullable=False, server_default="telegram"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("paused", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("min_percentage", sa.Numeric(7, 2)),
        sa.Column("verified_only", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("include_unverified", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("notify_new", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("notify_changes", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("notify_expiring", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", TZ, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "saved_filters",
        _uuid_pk(),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page", sa.String(64), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("params", pg.JSONB, nullable=False, server_default=EMPTY_JSON),
        _created(),
        sa.UniqueConstraint("user_id", "page", "name", name="uq_saved_filters_user_page_name"),
    )

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", pg.JSONB),
        sa.Column("updated_at", TZ, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in (
        "app_settings",
        "saved_filters",
        "notification_preferences",
        "watchlists",
        "monitored_products",
        "manual_verifications",
        "notifications",
        "scan_runs",
        "price_history",
        "offer_snapshots",
        "offers",
        "products",
        "discovery_sources",
        "users",
    ):
        op.drop_table(table, schema="coinback")
