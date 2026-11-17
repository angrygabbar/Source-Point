"""Turns connector observations into products, price history, offers and immutable snapshots."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.classifier.engine import Classification, classify_texts
from app.config import get_settings
from app.connectors.base import ProductObservation
from app.database.enums import EVIDENCE_RANK, AccessStatus, OfferStatus, SourceType
from app.database.models import DiscoverySource, Offer, OfferSnapshot, PriceHistory, Product
from app.discovery.url_validation import UrlValidationError, ValidatedUrl, validate_flipkart_url
from app.services.clock import utcnow
from app.services.offer_math import raw_advertised_percentage, recompute_offer
from app.services.settings_store import AppConfig

_LIMITS = {"brand": 255, "category": 255, "seller": 255, "variant": 255}


@dataclass
class IngestOutcome:
    product_id: uuid.UUID | None = None
    product_created: bool = False
    new_offer_ids: list[uuid.UUID] = field(default_factory=list)
    changed_offer_ids: list[uuid.UUID] = field(default_factory=list)
    offers_detected: int = 0
    non_coinback: int = 0
    skipped_reason: str | None = None


def add_snapshot(db: Session, offer: Offer, product: Product, change_type: str, evidence: dict[str, Any], now: datetime) -> None:
    db.add(
        OfferSnapshot(
            offer_id=offer.id,
            product_id=offer.product_id,
            reward_coins=offer.advertised_coins,
            estimated_coins=offer.estimated_coins,
            percentage=offer.advertised_percentage,
            cap=offer.reward_cap_coins,
            selling_price=product.current_price,
            status=offer.status,
            confidence=offer.confidence,
            change_type=change_type,
            evidence=evidence,
            captured_at=now,
        )
    )


def find_product(db: Session, v: ValidatedUrl) -> Product | None:
    if v.pid:
        product = db.scalar(select(Product).where(Product.flipkart_pid == v.pid))
        if product:
            return product
    return db.scalar(select(Product).where(Product.normalized_url == v.normalized_url))


def compute_discount(price: Decimal | None, mrp: Decimal | None) -> Decimal | None:
    if price is None or mrp is None or mrp <= 0 or price > mrp:
        return None
    return ((mrp - price) / mrp * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)


def apply_observation(product: Product, obs: ProductObservation) -> None:
    if obs.title:
        product.title = obs.title.strip()[:1000]
    for attr in ("brand", "category", "seller", "variant"):
        value = getattr(obs, attr)
        if value:
            setattr(product, attr, value.strip()[: _LIMITS[attr]])
    if obs.image_url and obs.image_url.startswith("https://"):
        product.image_url = obs.image_url[:2048]
    if obs.selling_price is not None:
        product.current_price = obs.selling_price
    if obs.mrp is not None:
        product.mrp = obs.mrp
    if obs.shipping_charge is not None:
        product.shipping_charge = obs.shipping_charge
    if obs.in_stock is not None:
        product.in_stock = obs.in_stock
    product.discount_percent = compute_discount(product.current_price, product.mrp)


def record_price(db: Session, product: Product, source_type: str, now: datetime, min_interval_minutes: int) -> bool:
    if product.current_price is None:
        return False
    last = db.scalar(
        select(PriceHistory).where(PriceHistory.product_id == product.id).order_by(PriceHistory.captured_at.desc()).limit(1)
    )
    current = (product.current_price, product.mrp, product.seller, product.in_stock, product.shipping_charge)
    if last is not None:
        previous = (last.selling_price, last.mrp, last.seller, last.in_stock, last.shipping_charge)
        if previous == current and now - last.captured_at < timedelta(minutes=min_interval_minutes):
            return False
    db.add(
        PriceHistory(
            product_id=product.id,
            selling_price=product.current_price,
            mrp=product.mrp,
            shipping_charge=product.shipping_charge,
            seller=product.seller,
            in_stock=product.in_stock,
            source_type=source_type,
            captured_at=now,
        )
    )
    return True


def _evidence(c: Classification, source_type: str, source_url: str | None, extra: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "source_url": source_url,
        "excerpt": c.description[:2000],
        "classification_reason": c.reason,
        "calculation_notes": notes,
        "observation": extra,
    }


def _create_offer(db: Session, product: Product, c: Classification, *, source: DiscoverySource | None, source_type: str,
                  source_url: str | None, extra: dict[str, Any], coin_value: Decimal | None, now: datetime) -> Offer:
    offer = Offer(
        id=uuid.uuid4(),
        product_id=product.id,
        title=c.title,
        description=c.description,
        reward_type=c.reward_type,
        is_up_to=c.is_up_to,
        advertised_coins=c.advertised_coins,
        per_spend_coins=c.per_spend_coins,
        per_spend_amount=c.per_spend_amount,
        reward_cap_coins=c.reward_cap_coins,
        min_eligible_purchase=c.min_eligible_purchase,
        max_eligible_purchase=c.max_eligible_purchase,
        eligible_purchase_amount=c.eligible_purchase_amount,
        status=c.status,
        confidence=c.confidence,
        classification_reason=c.reason,
        restrictions=c.restrictions,
        valid_until=c.valid_until,
        source_id=source.id if source else None,
        source_type=source_type,
        source_url=source_url,
        evidence_excerpt=c.description[:2000],
        fingerprint=c.fingerprint,
        first_detected_at=now,
        last_seen_at=now,
        last_changed_at=now,
    )
    math = recompute_offer(offer, product.current_price, coin_value, raw_pct=c.advertised_percentage, use_raw=True)
    db.add(offer)
    db.flush()
    add_snapshot(db, offer, product, "DETECTED", _evidence(c, source_type, source_url, extra, math.notes), now)
    return offer


def _update_offer(db: Session, offer: Offer, product: Product, c: Classification, *, source: DiscoverySource | None,
                  source_type: str, source_url: str | None, extra: dict[str, Any], coin_value: Decimal | None,
                  now: datetime) -> bool:
    """Returns True when the advertised reward changed or the offer re-appeared (notification-worthy)."""
    new_rank = EVIDENCE_RANK.get(source_type, 1)
    old_rank = EVIDENCE_RANK.get(offer.source_type, 1)
    inactive = offer.status in (OfferStatus.EXPIRED, OfferStatus.SOURCE_UNAVAILABLE)
    # Weaker evidence (e.g. a cached search snippet) never overrides or revives stronger evidence.
    if new_rank < old_rank:
        if not inactive:
            offer.last_seen_at = now
            recompute_offer(offer, product.current_price, coin_value)
        return False
    offer.last_seen_at = now
    reactivated = inactive
    if inactive and c.valid_until is not None and c.valid_until < now:
        return False
    raw_before = raw_advertised_percentage(offer)
    reward_changed = (
        raw_before != c.advertised_percentage
        or offer.advertised_coins != c.advertised_coins
        or offer.per_spend_coins != c.per_spend_coins
        or offer.per_spend_amount != c.per_spend_amount
        or offer.is_up_to != c.is_up_to
        or (c.reward_cap_coins is not None and offer.reward_cap_coins != c.reward_cap_coins)
    )
    previous_status = offer.status

    offer.advertised_coins = c.advertised_coins
    offer.per_spend_coins = c.per_spend_coins
    offer.per_spend_amount = c.per_spend_amount
    offer.is_up_to = c.is_up_to
    for attr in ("reward_cap_coins", "min_eligible_purchase", "max_eligible_purchase", "eligible_purchase_amount", "valid_until"):
        value = getattr(c, attr)
        if value is not None:
            setattr(offer, attr, value)
    offer.description = c.description
    offer.confidence = c.confidence
    offer.classification_reason = c.reason
    if c.restrictions:
        offer.restrictions = c.restrictions
    offer.source_id = source.id if source else offer.source_id
    offer.source_type = source_type
    offer.source_url = source_url or offer.source_url
    offer.evidence_excerpt = c.description[:2000]

    if previous_status in (OfferStatus.VERIFIED, OfferStatus.REJECTED) and not reactivated:
        if reward_changed:
            offer.status = OfferStatus.ACCOUNT_CHECK_REQUIRED
            offer.classification_reason = f"{c.reason} Reward terms changed since manual review."
    else:
        offer.status = c.status
    if reactivated:
        offer.expired_at = None

    math = recompute_offer(offer, product.current_price, coin_value, raw_pct=c.advertised_percentage, use_raw=True)
    if reward_changed or reactivated or offer.status != previous_status:
        offer.last_changed_at = now
        change = "REACTIVATED" if reactivated else "REWARD_CHANGED" if reward_changed else "STATUS_CHANGED"
        add_snapshot(db, offer, product, change, _evidence(c, source_type, source_url, extra, math.notes), now)
    return reward_changed or reactivated


def upsert_offers(db: Session, product: Product, texts: list[str], *, source: DiscoverySource | None, source_type: str,
                  source_url: str | None, extra: dict[str, Any], config: AppConfig, now: datetime,
                  complete_page: bool = False) -> IngestOutcome:
    outcome = IngestOutcome(product_id=product.id)
    seen: set[str] = set()
    for c in classify_texts(texts, source_type=source_type, now=now):
        if not c.is_coinback:
            outcome.non_coinback += 1
            continue
        outcome.offers_detected += 1
        fp = c.fingerprint
        if fp in seen:
            continue
        seen.add(fp)
        offer = db.scalar(select(Offer).where(Offer.product_id == product.id, Offer.fingerprint == fp))
        kwargs = dict(source=source, source_type=source_type, source_url=source_url, extra=extra, coin_value=config.coin_value, now=now)
        if offer is None:
            outcome.new_offer_ids.append(_create_offer(db, product, c, **kwargs).id)
        elif _update_offer(db, offer, product, c, **kwargs):
            outcome.changed_offer_ids.append(offer.id)

    if complete_page:
        stale = db.scalars(
            select(Offer).where(
                Offer.product_id == product.id,
                Offer.source_type == SourceType.PRODUCT_PAGE,
                Offer.status.notin_((OfferStatus.EXPIRED, OfferStatus.REJECTED)),
            )
        ).all()
        for offer in stale:
            if offer.fingerprint not in seen:
                offer.status = OfferStatus.EXPIRED
                offer.expired_at = now
                offer.last_changed_at = now
                add_snapshot(db, offer, product, "NO_LONGER_DISPLAYED", {"source_url": source_url, "reason": "Offer text no longer present on the product page."}, now)
    return outcome


def ingest_observation(db: Session, obs: ProductObservation, *, source: DiscoverySource | None, config: AppConfig,
                       now: datetime | None = None) -> IngestOutcome:
    now = now or utcnow()
    try:
        validated = validate_flipkart_url(obs.url, get_settings().flipkart_host_list)
    except UrlValidationError as exc:
        return IngestOutcome(skipped_reason=str(exc))
    if not validated.is_product_page:
        return IngestOutcome(skipped_reason="Not a product page URL.")

    product = find_product(db, validated)
    created = False
    if product is None:
        product = Product(
            id=uuid.uuid4(),
            product_url=validated.canonical_url,
            normalized_url=validated.normalized_url,
            original_url=obs.url,
            flipkart_pid=validated.pid,
            item_id=validated.item_id,
            source_id=source.id if source else None,
            first_seen_at=now,
        )
        db.add(product)
        db.flush()
        created = True
    elif product.archived_at is not None:
        return IngestOutcome(product_id=product.id, skipped_reason="Product archived by operator.")

    apply_observation(product, obs)
    record_price(db, product, obs.evidence_source, now, config.price_snapshot_min_interval_minutes)
    product.last_seen_at = now
    if obs.evidence_source in (SourceType.PRODUCT_PAGE, SourceType.THIRD_PARTY):
        product.last_checked_at = now
        product.access_status = AccessStatus.OK
        product.last_access_error = None
        product.consecutive_failures = 0

    outcome = upsert_offers(
        db, product, obs.offer_texts, source=source, source_type=obs.evidence_source, source_url=obs.url,
        extra=obs.evidence, config=config, now=now, complete_page=obs.complete_page,
    )
    outcome.product_created = created
    return outcome
