"""Explicit response shapes. Decimal values are encoded as JSON numbers by FastAPI's encoder."""

from __future__ import annotations

from typing import Any

from app.connectors.registry import connector_info
from app.database.models import (
    DiscoverySource,
    ManualVerification,
    MonitoredProduct,
    Notification,
    Offer,
    OfferSnapshot,
    PriceHistory,
    Product,
    ScanRun,
)


def offer_brief(o: Offer | None) -> dict[str, Any] | None:
    if o is None:
        return None
    return {
        "id": o.id,
        "title": o.title,
        "reward_type": o.reward_type,
        "is_up_to": o.is_up_to,
        "advertised_coins": o.advertised_coins,
        "advertised_percentage": o.advertised_percentage,
        "estimated_coins": o.estimated_coins,
        "reward_cap_coins": o.reward_cap_coins,
        "per_spend_coins": o.per_spend_coins,
        "per_spend_amount": o.per_spend_amount,
        "status": o.status,
        "confidence": o.confidence,
        "source_type": o.source_type,
        "valid_until": o.valid_until,
        "last_seen_at": o.last_seen_at,
    }


def product_mini(p: Product) -> dict[str, Any]:
    return {
        "id": p.id,
        "title": p.title,
        "brand": p.brand,
        "category": p.category,
        "image_url": p.image_url,
        "current_price": p.current_price,
        "mrp": p.mrp,
        "discount_percent": p.discount_percent,
        "seller": p.seller,
        "product_url": p.product_url,
        "flipkart_pid": p.flipkart_pid,
        "in_stock": p.in_stock,
        "access_status": p.access_status,
    }


def product_row(p: Product, best: Offer | None = None, monitored: bool = False) -> dict[str, Any]:
    return {
        **product_mini(p),
        "shipping_charge": p.shipping_charge,
        "variant": p.variant,
        "original_url": p.original_url,
        "last_access_error": p.last_access_error,
        "first_seen_at": p.first_seen_at,
        "last_seen_at": p.last_seen_at,
        "last_checked_at": p.last_checked_at,
        "archived_at": p.archived_at,
        "source_name": p.source.name if p.source else None,
        "is_monitored": bool(monitored),
        "best_offer": offer_brief(best),
    }


def offer_full(o: Offer, include_product: bool = True) -> dict[str, Any]:
    data = {
        **offer_brief(o),
        "product_id": o.product_id,
        "description": o.description,
        "min_eligible_purchase": o.min_eligible_purchase,
        "max_eligible_purchase": o.max_eligible_purchase,
        "eligible_purchase_amount": o.eligible_purchase_amount,
        "estimated_redemption_value": o.estimated_redemption_value,
        "actual_redemption_value": o.actual_redemption_value,
        "effective_cost_estimate": o.effective_cost_estimate,
        "classification_reason": o.classification_reason,
        "restrictions": o.restrictions or {},
        "terms": o.terms,
        "valid_from": o.valid_from,
        "source_url": o.source_url,
        "source_name": o.source.name if o.source else None,
        "evidence_excerpt": o.evidence_excerpt,
        "first_detected_at": o.first_detected_at,
        "last_changed_at": o.last_changed_at,
        "verified_at": o.verified_at,
        "expired_at": o.expired_at,
    }
    if include_product:
        data["product"] = product_mini(o.product)
    return data


def snapshot_out(s: OfferSnapshot) -> dict[str, Any]:
    return {
        "id": s.id,
        "offer_id": s.offer_id,
        "reward_coins": s.reward_coins,
        "estimated_coins": s.estimated_coins,
        "percentage": s.percentage,
        "cap": s.cap,
        "selling_price": s.selling_price,
        "status": s.status,
        "confidence": s.confidence,
        "change_type": s.change_type,
        "evidence": s.evidence or {},
        "captured_at": s.captured_at,
    }


def price_point(h: PriceHistory) -> dict[str, Any]:
    return {
        "captured_at": h.captured_at,
        "selling_price": h.selling_price,
        "mrp": h.mrp,
        "shipping_charge": h.shipping_charge,
        "seller": h.seller,
        "in_stock": h.in_stock,
        "source_type": h.source_type,
    }


def verification_out(v: ManualVerification, username: str | None = None) -> dict[str, Any]:
    return {
        "id": v.id,
        "offer_id": v.offer_id,
        "status": v.status,
        "advertised_reward_coins": v.advertised_reward_coins,
        "advertised_percentage": v.advertised_percentage,
        "actual_reward_coins": v.actual_reward_coins,
        "actual_percentage": v.actual_percentage,
        "eligible_purchase_amount": v.eligible_purchase_amount,
        "reward_cap_coins": v.reward_cap_coins,
        "actual_redemption_value": v.actual_redemption_value,
        "restrictions": v.restrictions,
        "expiry": v.expiry,
        "eligibility_notes": v.eligibility_notes,
        "notes": v.notes,
        "verified_by": username,
        "verified_at": v.verified_at,
    }


def source_out(s: DiscoverySource) -> dict[str, Any]:
    info = connector_info(s.connector_key)
    return {
        "id": s.id,
        "name": s.name,
        "source_type": s.source_type,
        "connector_key": s.connector_key,
        "enabled": s.enabled,
        "config": s.config or {},
        "auth_method": s.auth_method,
        "rate_limit_per_minute": s.rate_limit_per_minute,
        "permitted_use_notes": s.permitted_use_notes,
        "last_success_at": s.last_success_at,
        "last_error": s.last_error,
        "last_error_at": s.last_error_at,
        "consecutive_failures": s.consecutive_failures,
        "backoff_until": s.backoff_until,
        "supports_discovery": info.supports_discovery if info else False,
        "supports_product_fetch": info.supports_product_fetch if info else False,
    }


def scan_run_out(r: ScanRun, include_details: bool = False) -> dict[str, Any]:
    data = {
        "id": r.id,
        "trigger": r.trigger,
        "status": r.status,
        "source_id": r.source_id,
        "queued_at": r.queued_at,
        "started_at": r.started_at,
        "finished_at": r.finished_at,
        "duration_ms": r.duration_ms,
        "products_discovered": r.products_discovered,
        "products_processed": r.products_processed,
        "offers_detected": r.offers_detected,
        "offers_new": r.offers_new,
        "offers_expired": r.offers_expired,
        "notifications_queued": r.notifications_queued,
        "errors_count": r.errors_count,
        "progress": r.progress or {},
    }
    if include_details:
        data["details"] = r.details or {}
    return data


def notification_out(n: Notification, product_title: str | None = None) -> dict[str, Any]:
    return {
        "id": n.id,
        "product_id": n.product_id,
        "offer_id": n.offer_id,
        "product_title": product_title,
        "channel": n.channel,
        "chat_id": f"…{n.chat_id[-4:]}" if n.chat_id else None,
        "event_type": n.event_type,
        "message": n.message,
        "status": n.status,
        "retry_count": n.retry_count,
        "next_attempt_at": n.next_attempt_at,
        "last_error": n.last_error,
        "sent_at": n.sent_at,
        "created_at": n.created_at,
    }


def monitored_out(m: MonitoredProduct) -> dict[str, Any]:
    return {
        "id": m.id,
        "product_id": m.product_id,
        "enabled": m.enabled,
        "frequency_minutes": m.frequency_minutes,
        "last_processed_at": m.last_processed_at,
        "next_due_at": m.next_due_at,
        "created_at": m.created_at,
        "product": product_mini(m.product),
    }
