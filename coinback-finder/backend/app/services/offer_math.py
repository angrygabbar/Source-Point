from decimal import Decimal

from app.classifier.calculator import RewardMath, compute_reward
from app.database.enums import RewardType
from app.database.models import Offer


def raw_advertised_percentage(offer: Offer) -> Decimal | None:
    """The percentage stated by the source (not one derived from a confirmed eligible amount)."""
    if offer.reward_type == RewardType.PERCENTAGE:
        return offer.advertised_percentage
    if offer.reward_type == RewardType.CONDITIONAL_UP_TO and offer.advertised_coins is None:
        return offer.advertised_percentage
    return None


def recompute_offer(offer: Offer, selling_price: Decimal | None, coin_value: Decimal | None, *, raw_pct: Decimal | None = None,
                    use_raw: bool = False) -> RewardMath:
    math = compute_reward(
        reward_type=offer.reward_type,
        advertised_percentage=raw_pct if use_raw else raw_advertised_percentage(offer),
        advertised_coins=offer.advertised_coins,
        per_spend_coins=offer.per_spend_coins,
        per_spend_amount=offer.per_spend_amount,
        reward_cap_coins=offer.reward_cap_coins,
        eligible_purchase_amount=offer.eligible_purchase_amount,
        selling_price=selling_price,
        coin_value_inr=coin_value,
    )
    offer.advertised_percentage = math.advertised_percentage
    offer.estimated_coins = math.estimated_coins
    offer.estimated_redemption_value = math.estimated_redemption_value
    offer.effective_cost_estimate = math.effective_cost_estimate
    return math
