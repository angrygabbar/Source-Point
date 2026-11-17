import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.classifier.calculator import compute_reward
from app.classifier.engine import classify_texts
from app.database.enums import OfferStatus, RewardType, SourceType

FIXTURES = json.loads((Path(__file__).parent.parent / "fixtures" / "offer_texts.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", FIXTURES, ids=[c["text"] for c in FIXTURES])
def test_specification_table(case):
    results = classify_texts([case["text"]], source_type=SourceType.PRODUCT_PAGE)
    assert results, "expected a classification"
    c = results[0]
    assert c.reward_type == case["reward_type"]
    if "percentage" in case:
        expected = case["percentage"]
        assert (c.advertised_percentage is None) if expected is None else c.advertised_percentage == Decimal(expected)
    if "coins" in case:
        assert c.advertised_coins == case["coins"]
    if "up_to" in case:
        assert c.is_up_to is case["up_to"]


def test_search_snippet_never_verified():
    c = classify_texts(["Get 100% SuperCoins back on this product"], source_type=SourceType.PUBLIC_SEARCH)[0]
    assert c.status == OfferStatus.DETECTED
    assert "discovery evidence only" in c.reason


def test_cap_detected_from_up_to_coins_with_percentage():
    c = classify_texts(["Get 100% SuperCoins back, up to 500 SuperCoins"], source_type=SourceType.PRODUCT_PAGE)[0]
    assert c.reward_type == RewardType.PERCENTAGE
    assert c.reward_cap_coins == 500


def test_explicit_cap_phrase():
    c = classify_texts(["Get 50% SuperCoins back. Max 250 SuperCoins per order"], source_type=SourceType.PRODUCT_PAGE)[0]
    assert c.reward_cap_coins == 250


def test_context_enrichment_for_single_offer():
    texts = ["Get 100% SuperCoins back", "Maximum 300 SuperCoins. Valid till 30 Nov 2026. Only for Plus members"]
    coin = [c for c in classify_texts(texts, source_type=SourceType.PRODUCT_PAGE) if c.is_coinback]
    assert len(coin) == 1
    assert coin[0].reward_cap_coins == 300
    assert coin[0].valid_until is not None
    assert coin[0].status == OfferStatus.ACCOUNT_CHECK_REQUIRED
    assert coin[0].context_enriched


def test_reason_states_missing_cap():
    c = classify_texts(["Get 100% SuperCoins back"], source_type=SourceType.PRODUCT_PAGE)[0]
    assert "Maximum reward cap unavailable" in c.reason
    assert "Account-specific eligibility not confirmed" in c.reason


def test_fingerprint_stable_across_percentage_change():
    a = classify_texts(["Get 50% SuperCoins back"], source_type=SourceType.PRODUCT_PAGE)[0]
    b = classify_texts(["Get 100% SuperCoins back"], source_type=SourceType.PRODUCT_PAGE)[0]
    assert a.fingerprint == b.fingerprint


def test_fixed_reward_percentage_requires_eligible_amount():
    without = compute_reward(reward_type=RewardType.FIXED_COINS, advertised_percentage=None, advertised_coins=500,
                             per_spend_coins=None, per_spend_amount=None, reward_cap_coins=None,
                             eligible_purchase_amount=None, selling_price=Decimal("500"), coin_value_inr=None)
    assert without.advertised_percentage is None
    with_amount = compute_reward(reward_type=RewardType.FIXED_COINS, advertised_percentage=None, advertised_coins=500,
                                 per_spend_coins=None, per_spend_amount=None, reward_cap_coins=None,
                                 eligible_purchase_amount=Decimal("1000"), selling_price=Decimal("1000"), coin_value_inr=None)
    assert with_amount.advertised_percentage == Decimal("50.00")


def test_no_rupee_value_without_assumption():
    m = compute_reward(reward_type=RewardType.PERCENTAGE, advertised_percentage=Decimal("100"), advertised_coins=None,
                       per_spend_coins=None, per_spend_amount=None, reward_cap_coins=300,
                       eligible_purchase_amount=None, selling_price=Decimal("2000"), coin_value_inr=None)
    assert m.estimated_coins == 300
    assert m.estimated_redemption_value is None
    assert m.effective_cost_estimate is None


def test_estimates_with_configured_assumption():
    m = compute_reward(reward_type=RewardType.PERCENTAGE, advertised_percentage=Decimal("100"), advertised_coins=None,
                       per_spend_coins=None, per_spend_amount=None, reward_cap_coins=None,
                       eligible_purchase_amount=None, selling_price=Decimal("2000"), coin_value_inr=Decimal("0.5"))
    assert m.estimated_coins == 2000
    assert m.estimated_redemption_value == Decimal("1000.00")
    assert m.effective_cost_estimate == Decimal("1000.00")
