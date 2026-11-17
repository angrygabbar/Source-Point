"""CoinBack detection & classification engine.

Rules:
* Search snippets never produce VERIFIED; only manual verification does.
* "Up to" statements are conditional and never treated as guaranteed.
* Percentages for fixed or per-spend rewards are not calculated without a confirmed eligible amount.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from dateutil import parser as date_parser

from app.classifier import patterns as p
from app.database.enums import OfferStatus, RewardType, SourceType
from app.services.clock import IST, utcnow

MAX_PERCENTAGE = Decimal("1000")
MAX_CONTEXT_CHARS = 4000

EVIDENCE_LABEL = {
    SourceType.PUBLIC_SEARCH: "search result snippet",
    SourceType.PRODUCT_PAGE: "product page promotional text",
    SourceType.THIRD_PARTY: "authorized provider feed",
    SourceType.USER_SUBMITTED: "user-submitted product page",
    SourceType.MANUAL: "manually entered offer text",
}
BASE_CONFIDENCE = {
    SourceType.PUBLIC_SEARCH: Decimal("0.35"),
    SourceType.THIRD_PARTY: Decimal("0.55"),
    SourceType.PRODUCT_PAGE: Decimal("0.70"),
    SourceType.USER_SUBMITTED: Decimal("0.70"),
    SourceType.MANUAL: Decimal("0.60"),
}


@dataclass
class Classification:
    reward_type: str
    title: str
    description: str
    advertised_percentage: Decimal | None = None
    advertised_coins: int | None = None
    is_up_to: bool = False
    per_spend_coins: int | None = None
    per_spend_amount: Decimal | None = None
    reward_cap_coins: int | None = None
    min_eligible_purchase: Decimal | None = None
    max_eligible_purchase: Decimal | None = None
    eligible_purchase_amount: Decimal | None = None
    valid_until: datetime | None = None
    restrictions: dict[str, list[str]] = field(default_factory=dict)
    status: str = OfferStatus.DETECTED
    confidence: Decimal = Decimal("0")
    reason: str = ""
    context_enriched: bool = False

    @property
    def is_coinback(self) -> bool:
        return self.reward_type != RewardType.NOT_COINBACK

    @property
    def fingerprint(self) -> str:
        return offer_fingerprint(self.reward_type, self.title)


def offer_fingerprint(reward_type: str, title: str) -> str:
    """Stable identity for an offer statement; numbers are masked so reward changes are tracked on one offer."""
    masked = re.sub(r"[₹\d.,%]+", "#", title.lower())
    masked = " ".join(masked.split())[:160]
    return hashlib.sha256(f"{reward_type}|{masked}".encode()).hexdigest()


def _int(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(Decimal(raw.replace(",", "")))
    except (InvalidOperation, ValueError):
        return None


def _dec(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    try:
        return Decimal(raw.replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _overlaps(a: re.Match[str] | None, b: re.Match[str]) -> bool:
    return a is not None and a.start() < b.end() and b.start() < a.end()


def parse_validity(text: str, now: datetime | None = None) -> datetime | None:
    match = p.VALIDITY_RE.search(text)
    if not match:
        return None
    raw = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", match.group("date"), flags=re.IGNORECASE)
    local_now = (now or utcnow()).astimezone(IST)
    try:
        parsed = date_parser.parse(raw, dayfirst=True, default=datetime(local_now.year, 1, 1))
    except (ValueError, OverflowError):
        return None
    has_year = bool(re.search(r"\d{4}|\d{1,2}[/.-]\d{1,2}[/.-]\d{2}", raw))
    if not has_year and parsed.date() < (local_now - timedelta(days=30)).date():
        parsed = parsed.replace(year=parsed.year + 1)
    return datetime.combine(parsed.date(), time(23, 59, 59), tzinfo=IST).astimezone(timezone.utc)


def extract_restrictions(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for group, regexes in p.RESTRICTION_PATTERNS.items():
        hits: list[str] = []
        for regex in regexes:
            for m in regex.finditer(text):
                phrase = " ".join(m.group(0).split())
                if phrase.lower() not in {h.lower() for h in hits}:
                    hits.append(phrase)
        if hits:
            found[group] = hits[:6]
    return found


def _segments(texts: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for text in texts:
        if not isinstance(text, str):
            continue
        for part in p.SEGMENT_SPLIT_RE.split(text):
            seg = " ".join(part.split())[:1000]
            if len(seg) >= 6 and seg.lower() not in seen:
                seen.add(seg.lower())
                out.append(seg)
    return out


def _fill_terms(c: Classification, text: str, now: datetime | None) -> None:
    if c.reward_cap_coins is None and (m := p.CAP_RE.search(text)):
        c.reward_cap_coins = _int(m.group("cap"))
    if c.min_eligible_purchase is None and (m := p.MIN_PURCHASE_RE.search(text)):
        c.min_eligible_purchase = _dec(m.group("amt"))
    if c.max_eligible_purchase is None and (m := p.MAX_PURCHASE_RE.search(text)):
        c.max_eligible_purchase = _dec(m.group("amt"))
    if c.eligible_purchase_amount is None and (m := p.ELIGIBLE_AMOUNT_RE.search(text)):
        c.eligible_purchase_amount = _dec(m.group("amt"))
    if c.valid_until is None:
        c.valid_until = parse_validity(text, now)
    for group, hits in extract_restrictions(text).items():
        merged = c.restrictions.setdefault(group, [])
        merged.extend(h for h in hits if h not in merged)


def classify_segment(segment: str, now: datetime | None = None) -> Classification | None:
    if not p.COIN_RE.search(segment):
        if p.NON_COIN_RE.search(segment):
            return Classification(
                reward_type=RewardType.NOT_COINBACK,
                title=segment[:500],
                description=segment,
                reason="Bank, card or instant-discount offer; not a SuperCoin/CoinBack reward.",
            )
        return None

    if p.REDEEM_RE.search(segment) and not p.EARN_RE.search(segment):
        return Classification(
            reward_type=RewardType.NOT_COINBACK,
            title=segment[:500],
            description=segment,
            reason="SuperCoin redemption offer (spend coins), not a reward earned on purchase.",
        )

    rate = p.RATE_RE.search(segment)
    cap_match = p.CAP_RE.search(segment)
    pct_match = p.PCT_BEFORE_RE.search(segment) or p.PCT_AFTER_RE.search(segment)
    fixed = [m for m in p.FIXED_RE.finditer(segment) if not _overlaps(rate, m) and not _overlaps(cap_match, m)]

    c = Classification(reward_type=RewardType.NOT_COINBACK, title=segment[:500], description=segment)
    if cap_match:
        c.reward_cap_coins = _int(cap_match.group("cap"))

    if pct_match:
        pct = _dec(pct_match.group("pct"))
        if pct is None or pct <= 0 or pct > MAX_PERCENTAGE:
            return None
        c.advertised_percentage = pct
        c.is_up_to = bool(pct_match.group("upto"))
        c.reward_type = RewardType.CONDITIONAL_UP_TO if c.is_up_to else RewardType.PERCENTAGE
        if c.reward_cap_coins is None:
            for m in fixed:
                if m.group("upto"):
                    c.reward_cap_coins = _int(m.group("coins"))
                    break
    elif rate:
        c.reward_type = RewardType.PER_SPEND_RATE
        c.per_spend_coins = _int(rate.group("coins"))
        c.per_spend_amount = _dec(rate.group("amt"))
        if not c.per_spend_coins or not c.per_spend_amount:
            return None
    elif fixed:
        m = fixed[0]
        c.advertised_coins = _int(m.group("coins"))
        if not c.advertised_coins:
            return None
        c.is_up_to = bool(m.group("upto"))
        c.reward_type = RewardType.CONDITIONAL_UP_TO if c.is_up_to else RewardType.FIXED_COINS
    elif cap_match:
        return None
    else:
        return None

    _fill_terms(c, segment, now)
    return c


def _merge_key(c: Classification) -> tuple:
    return (c.reward_type, c.advertised_percentage, c.advertised_coins, c.per_spend_coins, c.per_spend_amount)


def _finalise(c: Classification, source_type: str) -> Classification:
    label = EVIDENCE_LABEL.get(source_type, "source text")

    if source_type == SourceType.PUBLIC_SEARCH:
        c.status = OfferStatus.DETECTED
    elif c.is_up_to or c.reward_type == RewardType.PER_SPEND_RATE or c.restrictions.get("customer") or c.restrictions.get("payment"):
        c.status = OfferStatus.ACCOUNT_CHECK_REQUIRED
    else:
        c.status = OfferStatus.UNVERIFIED

    conf = BASE_CONFIDENCE.get(source_type, Decimal("0.4"))
    conf += {
        RewardType.PERCENTAGE: Decimal("0.10"),
        RewardType.FIXED_COINS: Decimal("0.05"),
        RewardType.CONDITIONAL_UP_TO: Decimal("-0.15"),
    }.get(c.reward_type, Decimal("0"))
    if c.reward_cap_coins is not None:
        conf += Decimal("0.05")
    if c.valid_until is not None:
        conf += Decimal("0.03")
    if c.restrictions:
        conf -= Decimal("0.05")
    if c.context_enriched:
        conf -= Decimal("0.03")
    c.confidence = min(max(conf, Decimal("0.05")), Decimal("0.95")).quantize(Decimal("0.001"), ROUND_HALF_UP)

    parts: list[str] = []
    if c.reward_type == RewardType.PERCENTAGE:
        parts.append(f"{c.advertised_percentage.normalize():f}% SuperCoin reward detected in {label}.")
    elif c.reward_type == RewardType.CONDITIONAL_UP_TO and c.advertised_percentage is not None:
        parts.append(
            f"Up to {c.advertised_percentage.normalize():f}% SuperCoin reward detected in {label}. "
            "Conditional: 'up to' does not guarantee the full percentage."
        )
    elif c.reward_type == RewardType.CONDITIONAL_UP_TO:
        parts.append(f"Up to {c.advertised_coins:,} SuperCoins detected in {label}. Conditional; not a guaranteed amount.")
    elif c.reward_type == RewardType.FIXED_COINS:
        parts.append(f"Fixed reward of {c.advertised_coins:,} SuperCoins detected in {label}.")
        if c.eligible_purchase_amount is None:
            parts.append("Percentage not calculated: eligible purchase amount unknown.")
    elif c.reward_type == RewardType.PER_SPEND_RATE:
        parts.append(
            f"Rate of {c.per_spend_coins:,} SuperCoins per ₹{c.per_spend_amount.normalize():f} detected in {label}. "
            "Ratio not calculated until the eligible base is confirmed."
        )
    parts.append(
        f"Maximum reward cap: {c.reward_cap_coins:,} SuperCoins." if c.reward_cap_coins is not None
        else "Maximum reward cap unavailable."
    )
    if c.restrictions:
        detail = "; ".join(f"{k}: {', '.join(v)}" for k, v in c.restrictions.items())
        parts.append(f"Restrictions noted ({detail}).")
    if c.context_enriched:
        parts.append("Terms were matched from surrounding text on the same source.")
    if source_type == SourceType.PUBLIC_SEARCH:
        parts.append("Source is a search snippet: discovery evidence only, not proof of the offer.")
    parts.append("Account-specific eligibility not confirmed.")
    c.reason = " ".join(parts)
    return c


def classify_texts(texts: list[str], *, source_type: str, now: datetime | None = None) -> list[Classification]:
    segments = _segments(texts)
    results: list[Classification] = []
    by_key: dict[tuple, Classification] = {}
    for seg in segments:
        c = classify_segment(seg, now)
        if c is None:
            continue
        if not c.is_coinback:
            results.append(c)
            continue
        key = _merge_key(c)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = c
            results.append(c)
            continue
        for attr in ("reward_cap_coins", "min_eligible_purchase", "max_eligible_purchase", "eligible_purchase_amount", "valid_until"):
            if getattr(existing, attr) is None and getattr(c, attr) is not None:
                setattr(existing, attr, getattr(c, attr))
        # Prefer the shorter statement as the canonical title.
        if len(c.title) < len(existing.title):
            existing.title, existing.description = c.title, c.description

    coin_offers = [c for c in results if c.is_coinback]
    if len(coin_offers) == 1 and len(segments) > 1:
        only = coin_offers[0]
        before = replace(only, restrictions={k: list(v) for k, v in only.restrictions.items()})
        _fill_terms(only, " ".join(segments)[:MAX_CONTEXT_CHARS], now)
        only.context_enriched = (
            only.reward_cap_coins != before.reward_cap_coins
            or only.valid_until != before.valid_until
            or only.min_eligible_purchase != before.min_eligible_purchase
            or only.restrictions != before.restrictions
        )
        only.description = " ".join(segments)[:MAX_CONTEXT_CHARS]

    for c in coin_offers:
        _finalise(c, source_type)
    return results
