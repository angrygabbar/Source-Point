"""Manual verification: the only path that can mark an offer VERIFIED."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.database.enums import OfferStatus, VerificationStatus
from app.database.models import ManualVerification, Offer, User
from app.services.clock import utcnow
from app.services.ingestion import add_snapshot
from app.services.offer_math import recompute_offer
from app.services.settings_store import get_app_config


@dataclass
class VerificationInput:
    status: str
    actual_reward_coins: int | None = None
    eligible_purchase_amount: Decimal | None = None
    reward_cap_coins: int | None = None
    actual_redemption_value: Decimal | None = None
    restrictions: str | None = None
    expiry: datetime | None = None
    eligibility_notes: str | None = None
    notes: str | None = None
    observed_at: datetime | None = None


def _actual_percentage(coins: int | None, amount: Decimal | None) -> Decimal | None:
    if coins is None or not amount or amount <= 0:
        return None
    return (Decimal(coins) / amount * 100).quantize(Decimal("0.01"), ROUND_HALF_UP)


def record_verification(db: Session, offer: Offer, data: VerificationInput, user: User) -> ManualVerification:
    now = utcnow()
    observed = min(data.observed_at, now) if data.observed_at else now
    product = offer.product
    advertised_coins_before = offer.advertised_coins if offer.advertised_coins is not None else offer.estimated_coins
    advertised_pct_before = offer.advertised_percentage

    if data.status != VerificationStatus.REJECTED:
        if data.eligible_purchase_amount is not None:
            offer.eligible_purchase_amount = data.eligible_purchase_amount
        if data.reward_cap_coins is not None:
            offer.reward_cap_coins = data.reward_cap_coins
        if data.actual_redemption_value is not None:
            offer.actual_redemption_value = data.actual_redemption_value
        if data.expiry is not None:
            offer.valid_until = data.expiry
        if data.restrictions:
            offer.restrictions = {**(offer.restrictions or {}), "verified": [data.restrictions[:500]]}
        recompute_offer(offer, product.current_price, get_app_config(db).coin_value)

    offer.status = {
        VerificationStatus.VERIFIED: OfferStatus.VERIFIED,
        VerificationStatus.REJECTED: OfferStatus.REJECTED,
        VerificationStatus.ACCOUNT_CHECK_REQUIRED: OfferStatus.ACCOUNT_CHECK_REQUIRED,
    }[VerificationStatus(data.status)]
    offer.verified_at = observed if offer.status == OfferStatus.VERIFIED else offer.verified_at
    offer.last_changed_at = now

    record = ManualVerification(
        offer_id=offer.id,
        product_id=offer.product_id,
        status=data.status,
        advertised_reward_coins=advertised_coins_before,
        advertised_percentage=advertised_pct_before,
        actual_reward_coins=data.actual_reward_coins,
        actual_percentage=_actual_percentage(data.actual_reward_coins, data.eligible_purchase_amount or offer.eligible_purchase_amount),
        eligible_purchase_amount=data.eligible_purchase_amount,
        reward_cap_coins=data.reward_cap_coins,
        actual_redemption_value=data.actual_redemption_value,
        restrictions=data.restrictions,
        expiry=data.expiry,
        eligibility_notes=data.eligibility_notes,
        notes=data.notes,
        verified_by=user.id,
        verified_at=observed,
    )
    db.add(record)
    db.flush()
    add_snapshot(
        db, offer, product, f"MANUAL_{data.status}",
        {"type": "manual_verification", "verification_id": str(record.id), "actual_reward_coins": data.actual_reward_coins,
         "notes": data.notes, "eligibility_notes": data.eligibility_notes, "verified_by": user.username},
        now,
    )
    db.commit()
    db.refresh(record)
    return record
