"""SQLAlchemy ORM models. All timestamps are stored in UTC (timestamptz)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.database.enums import AccessStatus, NotificationStatus, OfferStatus, ScanStatus


class Base(DeclarativeBase):
    pass


Money = Numeric(12, 2)
TZ = DateTime(timezone=True)


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created() -> Mapped[datetime]:
    return mapped_column(TZ, nullable=False, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _pk()
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    sourcepoint_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("public.user.id", ondelete="CASCADE"), unique=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = _created()


class DiscoverySource(Base):
    __tablename__ = "discovery_sources"

    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    connector_key: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # Non-secret configuration only. Secrets are referenced by environment variable name.
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    auth_method: Mapped[str] = mapped_column(String(32), nullable=False, server_default="none")
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")
    permitted_use_notes: Mapped[str | None] = mapped_column(Text)
    last_success_at: Mapped[datetime | None] = mapped_column(TZ)
    last_error: Mapped[str | None] = mapped_column(Text)
    last_error_at: Mapped[datetime | None] = mapped_column(TZ)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    backoff_until: Mapped[datetime | None] = mapped_column(TZ)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now(), onupdate=func.now())


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("uq_products_flipkart_pid", "flipkart_pid", unique=True, postgresql_where=text("flipkart_pid IS NOT NULL")),
        Index("ix_products_category", "category"),
        Index("ix_products_brand", "brand"),
        Index("ix_products_last_checked", "last_checked_at"),
        Index("ix_products_title_trgm", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
    )

    id: Mapped[uuid.UUID] = _pk()
    flipkart_pid: Mapped[str | None] = mapped_column(String(64))
    item_id: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(255))
    product_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    original_url: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    seller: Mapped[str | None] = mapped_column(String(255))
    current_price: Mapped[Decimal | None] = mapped_column(Money)
    mrp: Mapped[Decimal | None] = mapped_column(Money)
    discount_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    shipping_charge: Mapped[Decimal | None] = mapped_column(Money)
    in_stock: Mapped[bool | None] = mapped_column(Boolean)
    variant: Mapped[str | None] = mapped_column(String(255))
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("discovery_sources.id", ondelete="SET NULL"))
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    access_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=AccessStatus.PENDING.value)
    last_access_error: Mapped[str | None] = mapped_column(Text)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    first_seen_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(TZ)
    last_checked_at: Mapped[datetime | None] = mapped_column(TZ)
    archived_at: Mapped[datetime | None] = mapped_column(TZ)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now(), onupdate=func.now())

    source: Mapped[DiscoverySource | None] = relationship(lazy="joined")
    offers: Mapped[list[Offer]] = relationship(back_populates="product", order_by="Offer.last_seen_at.desc()")


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (
        UniqueConstraint("product_id", "fingerprint", name="uq_offers_product_fingerprint"),
        Index("ix_offers_advertised_percentage", "advertised_percentage"),
        Index("ix_offers_status_valid_until", "status", "valid_until"),
        Index("ix_offers_first_detected", "first_detected_at"),
        Index("ix_offers_product", "product_id"),
    )

    id: Mapped[uuid.UUID] = _pk()
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    reward_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_up_to: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    advertised_coins: Mapped[int | None] = mapped_column(Integer)
    advertised_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    per_spend_coins: Mapped[int | None] = mapped_column(Integer)
    per_spend_amount: Mapped[Decimal | None] = mapped_column(Money)
    reward_cap_coins: Mapped[int | None] = mapped_column(Integer)
    min_eligible_purchase: Mapped[Decimal | None] = mapped_column(Money)
    max_eligible_purchase: Mapped[Decimal | None] = mapped_column(Money)
    eligible_purchase_amount: Mapped[Decimal | None] = mapped_column(Money)
    # Derived/estimated values are stored separately from advertised and verified values.
    estimated_coins: Mapped[int | None] = mapped_column(Integer)
    estimated_redemption_value: Mapped[Decimal | None] = mapped_column(Money)
    actual_redemption_value: Mapped[Decimal | None] = mapped_column(Money)
    effective_cost_estimate: Mapped[Decimal | None] = mapped_column(Money)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=OfferStatus.DETECTED.value)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    classification_reason: Mapped[str | None] = mapped_column(Text)
    restrictions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    terms: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[datetime | None] = mapped_column(TZ)
    valid_until: Mapped[datetime | None] = mapped_column(TZ)
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("discovery_sources.id", ondelete="SET NULL"))
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    evidence_excerpt: Mapped[str | None] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    first_detected_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())
    last_changed_at: Mapped[datetime | None] = mapped_column(TZ)
    verified_at: Mapped[datetime | None] = mapped_column(TZ)
    expired_at: Mapped[datetime | None] = mapped_column(TZ)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now(), onupdate=func.now())

    product: Mapped[Product] = relationship(back_populates="offers")
    source: Mapped[DiscoverySource | None] = relationship(lazy="joined")


class OfferSnapshot(Base):
    """Immutable history row. Never updated after insert."""

    __tablename__ = "offer_snapshots"
    __table_args__ = (Index("ix_offer_snapshots_offer_time", "offer_id", "captured_at"),)

    id: Mapped[uuid.UUID] = _pk()
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    reward_coins: Mapped[int | None] = mapped_column(Integer)
    estimated_coins: Mapped[int | None] = mapped_column(Integer)
    percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    cap: Mapped[int | None] = mapped_column(Integer)
    selling_price: Mapped[Decimal | None] = mapped_column(Money)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    captured_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())


class PriceHistory(Base):
    """Immutable price observation."""

    __tablename__ = "price_history"
    __table_args__ = (Index("ix_price_history_product_time", "product_id", "captured_at"),)

    id: Mapped[uuid.UUID] = _pk()
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    selling_price: Mapped[Decimal | None] = mapped_column(Money)
    mrp: Mapped[Decimal | None] = mapped_column(Money)
    shipping_charge: Mapped[Decimal | None] = mapped_column(Money)
    seller: Mapped[str | None] = mapped_column(String(255))
    in_stock: Mapped[bool | None] = mapped_column(Boolean)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())


class ScanRun(Base):
    __tablename__ = "scan_runs"
    __table_args__ = (
        Index("ix_scan_runs_status", "status"),
        Index("ix_scan_runs_started", "started_at"),
    )

    id: Mapped[uuid.UUID] = _pk()
    trigger: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=ScanStatus.QUEUED.value)
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("discovery_sources.id", ondelete="SET NULL"))
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    queued_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(TZ)
    finished_at: Mapped[datetime | None] = mapped_column(TZ)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    products_discovered: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    products_processed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    offers_detected: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    offers_new: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    offers_expired: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    notifications_queued: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    progress: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_notifications_event_key"),
        Index("ix_notifications_status_next", "status", "next_attempt_at"),
        Index("ix_notifications_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = _pk()
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    offer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("offers.id", ondelete="SET NULL"))
    channel: Mapped[str] = mapped_column(String(32), nullable=False, server_default="telegram")
    chat_id: Mapped[str | None] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_key: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=NotificationStatus.PENDING.value)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    next_attempt_at: Mapped[datetime | None] = mapped_column(TZ)
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(TZ)
    created_at: Mapped[datetime] = _created()


class ManualVerification(Base):
    __tablename__ = "manual_verifications"
    __table_args__ = (Index("ix_manual_verifications_offer", "offer_id", "verified_at"),)

    id: Mapped[uuid.UUID] = _pk()
    offer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    advertised_reward_coins: Mapped[int | None] = mapped_column(Integer)
    advertised_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    actual_reward_coins: Mapped[int | None] = mapped_column(Integer)
    actual_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    eligible_purchase_amount: Mapped[Decimal | None] = mapped_column(Money)
    reward_cap_coins: Mapped[int | None] = mapped_column(Integer)
    actual_redemption_value: Mapped[Decimal | None] = mapped_column(Money)
    restrictions: Mapped[str | None] = mapped_column(Text)
    expiry: Mapped[datetime | None] = mapped_column(TZ)
    eligibility_notes: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now())


class MonitoredProduct(Base):
    __tablename__ = "monitored_products"
    __table_args__ = (Index("ix_monitored_due", "enabled", "next_due_at"),)

    id: Mapped[uuid.UUID] = _pk()
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    frequency_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default="15")
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    last_processed_at: Mapped[datetime | None] = mapped_column(TZ)
    next_due_at: Mapped[datetime | None] = mapped_column(TZ)
    created_at: Mapped[datetime] = _created()

    product: Mapped[Product] = relationship(lazy="joined")


class Watchlist(Base):
    __tablename__ = "watchlists"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_watchlists_user_product"),)

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    target_price: Mapped[Decimal | None] = mapped_column(Money)
    target_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    created_at: Mapped[datetime] = _created()

    product: Mapped[Product] = relationship(lazy="joined")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = _pk()
    scope: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, server_default="global")
    channel: Mapped[str] = mapped_column(String(32), nullable=False, server_default="telegram")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # NULL = all CoinBack offers; otherwise the minimum advertised percentage (10/25/50/75/100).
    min_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    verified_only: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    include_unverified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    notify_new: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    notify_changes: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    notify_expiring: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    updated_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now(), onupdate=func.now())


class SavedFilter(Base):
    __tablename__ = "saved_filters"
    __table_args__ = (UniqueConstraint("user_id", "page", "name", name="uq_saved_filters_user_page_name"),)

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    page: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at: Mapped[datetime] = _created()


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(TZ, nullable=False, server_default=func.now(), onupdate=func.now())
