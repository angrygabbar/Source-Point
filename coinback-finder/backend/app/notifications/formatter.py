"""Telegram message formatting (HTML parse mode, all dynamic values escaped)."""

from __future__ import annotations

from decimal import Decimal
from html import escape

from app.database.enums import NotificationEvent, OfferStatus, RewardType
from app.database.models import Offer, Product
from app.services.clock import format_ist

STATUS_LABEL = {
    OfferStatus.DETECTED: "Detected (unverified)",
    OfferStatus.UNVERIFIED: "Unverified",
    OfferStatus.ACCOUNT_CHECK_REQUIRED: "Account Check Required",
    OfferStatus.VERIFIED: "Verified",
    OfferStatus.REJECTED: "Rejected",
    OfferStatus.EXPIRED: "Expired",
    OfferStatus.SOURCE_UNAVAILABLE: "Source Unavailable",
}
SOURCE_LABEL = {
    "PUBLIC_SEARCH": "Search result snippet",
    "PRODUCT_PAGE": "Promotional description (product page)",
    "THIRD_PARTY": "Authorized provider feed",
    "USER_SUBMITTED": "User-submitted product",
    "MANUAL": "Manual entry",
}
HEADLINE = {
    NotificationEvent.NEW_OFFER: "NEW COINBACK OFFER",
    NotificationEvent.OFFER_CHANGED: "COINBACK OFFER CHANGED",
    NotificationEvent.OFFER_EXPIRING: "COINBACK OFFER EXPIRING",
}


def format_inr(amount: Decimal | float | None) -> str:
    if amount is None:
        return "Not available"
    value = Decimal(str(amount))
    value = value.quantize(Decimal("1")) if value == value.to_integral_value() else value.quantize(Decimal("0.01"))
    sign = "-" if value < 0 else ""
    integer, _, fraction = f"{abs(value):f}".partition(".")
    if len(integer) > 3:
        head, tail = integer[:-3], integer[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        integer = ",".join([*groups, tail])
    return f"{sign}₹{integer}" + (f".{fraction}" if fraction else "")


def format_pct(value: Decimal | None) -> str:
    return "Not available" if value is None else f"{value.normalize():f}%"


def offer_message(event: str, offer: Offer, product: Product) -> str:
    e = escape
    coins_line: str
    if offer.advertised_coins is not None:
        coins_line = f"{offer.advertised_coins:,}"
    elif offer.estimated_coins is not None:
        coins_line = f"{offer.estimated_coins:,} (estimate at listed price)"
    else:
        coins_line = "Not available"
    pct = format_pct(offer.advertised_percentage)
    if offer.is_up_to and offer.advertised_percentage is not None:
        pct = f"Up to {pct} (conditional)"
    if offer.reward_type == RewardType.PER_SPEND_RATE and offer.per_spend_coins and offer.per_spend_amount:
        pct = f"{offer.per_spend_coins} coins per {format_inr(offer.per_spend_amount)} (ratio unconfirmed)"
    cap = f"{offer.reward_cap_coins:,} SuperCoins" if offer.reward_cap_coins is not None else "Not confirmed"

    lines = [
        f"<b>{HEADLINE.get(event, 'COINBACK UPDATE')}</b>",
        f"Product: {e(product.title or 'Title not available')}",
        f"Price: {format_inr(product.current_price)}",
        f"Advertised SuperCoins: {e(coins_line)}",
        f"Advertised CoinBack: {e(pct)}",
        f"Maximum Reward: {e(cap)}",
        f"Status: {STATUS_LABEL.get(offer.status, offer.status)}",
        f"Source: {SOURCE_LABEL.get(offer.source_type, offer.source_type)}",
        f"Detected: {format_ist(offer.first_detected_at, '%I:%M %p, %d %b')}",
    ]
    if offer.valid_until:
        lines.append(f"Valid until: {format_ist(offer.valid_until, '%d %b %Y')}")
    if offer.status != OfferStatus.VERIFIED:
        lines.append("<i>Unverified: account-specific eligibility not confirmed.</i>")
    lines.append("Verify actual eligibility before purchase.")
    lines.append(f"Product URL: {e(product.product_url)}")
    return "\n".join(lines)
