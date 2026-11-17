"""Reward arithmetic. Advertised, estimated and verified values are kept separate."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from app.database.enums import RewardType

TWO = Decimal("0.01")


@dataclass
class RewardMath:
    advertised_percentage: Decimal | None
    estimated_coins: int | None
    estimated_redemption_value: Decimal | None
    effective_cost_estimate: Decimal | None
    notes: list[str] = field(default_factory=list)


def compute_reward(
    *,
    reward_type: str,
    advertised_percentage: Decimal | None,
    advertised_coins: int | None,
    per_spend_coins: int | None,
    per_spend_amount: Decimal | None,
    reward_cap_coins: int | None,
    eligible_purchase_amount: Decimal | None,
    selling_price: Decimal | None,
    coin_value_inr: Decimal | None,
) -> RewardMath:
    notes: list[str] = []
    pct = advertised_percentage

    # Advertised CoinBack % = advertised coins / eligible purchase amount × 100, only with a confirmed amount.
    if pct is None and eligible_purchase_amount and eligible_purchase_amount > 0:
        if advertised_coins:
            pct = (Decimal(advertised_coins) / eligible_purchase_amount * 100).quantize(TWO, ROUND_HALF_UP)
            notes.append("Percentage calculated from confirmed eligible purchase amount.")
        elif reward_type == RewardType.PER_SPEND_RATE and per_spend_coins and per_spend_amount:
            pct = (Decimal(per_spend_coins) / per_spend_amount * 100).quantize(TWO, ROUND_HALF_UP)
            notes.append("Rate converted to percentage using confirmed eligible base.")

    base = eligible_purchase_amount or selling_price
    if base is not None and eligible_purchase_amount is None:
        notes.append("Estimates use the listed selling price as the eligible amount.")

    coins: int | None = None
    if reward_type in (RewardType.PERCENTAGE, RewardType.CONDITIONAL_UP_TO) and advertised_percentage is not None:
        if base is not None:
            coins = int((advertised_percentage * base / 100).to_integral_value(ROUND_FLOOR))
    elif advertised_coins is not None:
        coins = advertised_coins
    elif reward_type == RewardType.PER_SPEND_RATE and per_spend_coins and per_spend_amount and base is not None:
        coins = int((base / per_spend_amount).to_integral_value(ROUND_FLOOR)) * per_spend_coins

    if coins is not None and reward_cap_coins is not None and coins > reward_cap_coins:
        coins = reward_cap_coins
        notes.append("Estimated coins limited by the advertised cap.")
    if reward_type == RewardType.CONDITIONAL_UP_TO and coins is not None:
        notes.append("'Up to' offer: estimated coins are an upper bound, not a guarantee.")

    value: Decimal | None = None
    effective: Decimal | None = None
    if coins is not None and coin_value_inr is not None:
        value = (Decimal(coins) * coin_value_inr).quantize(TWO, ROUND_HALF_UP)
        notes.append("Redemption value uses the configured SuperCoin conversion assumption.")
        if selling_price is not None:
            effective = max(selling_price - value, Decimal("0")).quantize(TWO, ROUND_HALF_UP)
    elif coins is not None:
        notes.append("No SuperCoin conversion value configured; redemption value not estimated.")

    return RewardMath(
        advertised_percentage=pct,
        estimated_coins=coins,
        estimated_redemption_value=value,
        effective_cost_estimate=effective,
        notes=notes,
    )
