"""Filterable list queries shared by list endpoints and exports. Sort keys are whitelisted."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import aliased, contains_eager

from app.api.deps import like_pattern
from app.database.enums import INACTIVE_OFFER_STATUSES, OfferStatus
from app.database.models import MonitoredProduct, Offer, Product
from app.services.clock import utcnow


def best_offer_alias():
    sub = (
        select(Offer)
        .where(Offer.status.notin_(INACTIVE_OFFER_STATUSES))
        .distinct(Offer.product_id)
        .order_by(
            Offer.product_id,
            Offer.advertised_percentage.desc().nulls_last(),
            Offer.estimated_coins.desc().nulls_last(),
            Offer.last_seen_at.desc(),
        )
        .subquery("best_offer")
    )
    return aliased(Offer, sub)


def active_offer_clause(now: datetime | None = None):
    now = now or utcnow()
    return (Offer.status.notin_(INACTIVE_OFFER_STATUSES)) & (or_(Offer.valid_until.is_(None), Offer.valid_until > now))


@dataclass
class ProductFilters:
    q: str | None = None
    category: str | None = None
    brand: str | None = None
    seller: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    min_pct: Decimal | None = None
    max_pct: Decimal | None = None
    statuses: list[str] = field(default_factory=list)
    source_types: list[str] = field(default_factory=list)
    access_statuses: list[str] = field(default_factory=list)
    has_offer: bool | None = None
    monitored: bool | None = None
    ids: list = field(default_factory=list)


def product_query(f: ProductFilters, sort: str | None, order: str) -> Select:
    bo = best_offer_alias()
    monitored = (
        select(MonitoredProduct.id)
        .where(MonitoredProduct.product_id == Product.id, MonitoredProduct.enabled.is_(True))
        .exists()
    )
    stmt = select(Product, bo, monitored.label("is_monitored")).outerjoin(bo, bo.product_id == Product.id)
    stmt = stmt.where(Product.archived_at.is_(None))

    if f.ids:
        stmt = stmt.where(Product.id.in_(f.ids))
    if f.q:
        pattern = like_pattern(f.q.strip())
        stmt = stmt.where(or_(Product.title.ilike(pattern, escape="\\"), Product.brand.ilike(pattern, escape="\\"),
                              Product.flipkart_pid.ilike(pattern, escape="\\")))
    if f.category:
        stmt = stmt.where(Product.category == f.category)
    if f.brand:
        stmt = stmt.where(Product.brand == f.brand)
    if f.seller:
        stmt = stmt.where(Product.seller == f.seller)
    if f.min_price is not None:
        stmt = stmt.where(Product.current_price >= f.min_price)
    if f.max_price is not None:
        stmt = stmt.where(Product.current_price <= f.max_price)
    if f.min_pct is not None:
        stmt = stmt.where(bo.advertised_percentage >= f.min_pct)
    if f.max_pct is not None:
        stmt = stmt.where(bo.advertised_percentage <= f.max_pct)
    if f.statuses:
        stmt = stmt.where(bo.status.in_(f.statuses))
    if f.source_types:
        stmt = stmt.where(bo.source_type.in_(f.source_types))
    if f.access_statuses:
        stmt = stmt.where(Product.access_status.in_(f.access_statuses))
    if f.has_offer is True:
        stmt = stmt.where(bo.id.is_not(None))
    elif f.has_offer is False:
        stmt = stmt.where(bo.id.is_(None))
    if f.monitored is not None:
        stmt = stmt.where(monitored if f.monitored else ~monitored)

    sorts = {
        "title": Product.title,
        "brand": Product.brand,
        "category": Product.category,
        "price": Product.current_price,
        "mrp": Product.mrp,
        "discount": Product.discount_percent,
        "seller": Product.seller,
        "last_checked": Product.last_checked_at,
        "first_seen": Product.first_seen_at,
        "pct": bo.advertised_percentage,
        "coins": func.coalesce(bo.advertised_coins, bo.estimated_coins),
        "cap": bo.reward_cap_coins,
        "status": bo.status,
        "source": bo.source_type,
    }
    column = sorts.get(sort or "", Product.last_seen_at)
    direction = column.asc().nulls_last() if order == "asc" else column.desc().nulls_last()
    return stmt.order_by(direction, Product.id)


@dataclass
class OfferFilters:
    q: str | None = None
    statuses: list[str] = field(default_factory=list)
    reward_types: list[str] = field(default_factory=list)
    source_types: list[str] = field(default_factory=list)
    min_pct: Decimal | None = None
    max_pct: Decimal | None = None
    pct_mode: str | None = None  # exact_100 | above_100 | gte_100
    capped: bool | None = None
    verified: bool | None = None
    up_to: bool | None = None
    min_coins: int | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    category: str | None = None
    active_only: bool = True
    detected_since: datetime | None = None
    product_id: object | None = None
    expiring_before: datetime | None = None


def offer_query(f: OfferFilters, sort: str | None, order: str) -> Select:
    stmt = (
        select(Offer)
        .join(Product, Product.id == Offer.product_id)
        .options(contains_eager(Offer.product))
        .where(Product.archived_at.is_(None))
    )
    if f.active_only:
        stmt = stmt.where(active_offer_clause())
    if f.product_id:
        stmt = stmt.where(Offer.product_id == f.product_id)
    if f.q:
        pattern = like_pattern(f.q.strip())
        stmt = stmt.where(or_(Product.title.ilike(pattern, escape="\\"), Product.brand.ilike(pattern, escape="\\"),
                              Offer.title.ilike(pattern, escape="\\")))
    if f.statuses:
        stmt = stmt.where(Offer.status.in_(f.statuses))
    if f.reward_types:
        stmt = stmt.where(Offer.reward_type.in_(f.reward_types))
    if f.source_types:
        stmt = stmt.where(Offer.source_type.in_(f.source_types))
    if f.pct_mode == "exact_100":
        stmt = stmt.where(Offer.advertised_percentage == 100)
    elif f.pct_mode == "above_100":
        stmt = stmt.where(Offer.advertised_percentage > 100)
    elif f.pct_mode == "gte_100":
        stmt = stmt.where(Offer.advertised_percentage >= 100)
    if f.min_pct is not None:
        stmt = stmt.where(Offer.advertised_percentage >= f.min_pct)
    if f.max_pct is not None:
        stmt = stmt.where(Offer.advertised_percentage <= f.max_pct)
    if f.capped is True:
        stmt = stmt.where(Offer.reward_cap_coins.is_not(None))
    elif f.capped is False:
        stmt = stmt.where(Offer.reward_cap_coins.is_(None))
    if f.verified is True:
        stmt = stmt.where(Offer.status == OfferStatus.VERIFIED)
    elif f.verified is False:
        stmt = stmt.where(Offer.status != OfferStatus.VERIFIED)
    if f.up_to is True:
        stmt = stmt.where(Offer.is_up_to.is_(True))
    elif f.up_to is False:
        stmt = stmt.where(Offer.is_up_to.is_(False))
    if f.min_coins is not None:
        stmt = stmt.where(func.coalesce(Offer.advertised_coins, Offer.estimated_coins) >= f.min_coins)
    if f.min_price is not None:
        stmt = stmt.where(Product.current_price >= f.min_price)
    if f.max_price is not None:
        stmt = stmt.where(Product.current_price <= f.max_price)
    if f.category:
        stmt = stmt.where(Product.category == f.category)
    if f.detected_since is not None:
        stmt = stmt.where(Offer.first_detected_at >= f.detected_since)
    if f.expiring_before is not None:
        stmt = stmt.where(Offer.valid_until.is_not(None), Offer.valid_until <= f.expiring_before)

    sorts = {
        "pct": Offer.advertised_percentage,
        "coins": func.coalesce(Offer.advertised_coins, Offer.estimated_coins),
        "cap": Offer.reward_cap_coins,
        "price": Product.current_price,
        "detected": Offer.first_detected_at,
        "last_seen": Offer.last_seen_at,
        "changed": Offer.last_changed_at,
        "confidence": Offer.confidence,
        "expiry": Offer.valid_until,
        "title": Product.title,
        "status": Offer.status,
        "effective_cost": Offer.effective_cost_estimate,
    }
    column = sorts.get(sort or "", Offer.first_detected_at)
    direction = column.asc().nulls_last() if order == "asc" else column.desc().nulls_last()
    return stmt.order_by(direction, Offer.id)
