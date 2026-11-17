"""User-submitted product URLs: validation, normalisation, deduplication and queueing."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.enums import AccessStatus
from app.database.models import DiscoverySource, Product, User
from app.discovery.url_validation import UrlValidationError, validate_flipkart_url
from app.services.clock import utcnow
from app.services.ingestion import find_product
from app.services.monitoring import ensure_monitored
from app.services.settings_store import get_app_config

NOT_PERMITTED_MESSAGE = (
    "Automated product page access is not enabled, so price and offer details cannot be collected automatically. "
    "Record offers and prices manually, or enable an authorized source."
)


def submit_product_url(db: Session, url: str, *, user: User, monitor: bool) -> tuple[Product, bool]:
    settings = get_settings()
    validated = validate_flipkart_url(url, settings.flipkart_host_list)
    if not validated.is_product_page:
        raise UrlValidationError("URL is not a Flipkart product page (expected a path containing /p/itm…).")

    now = utcnow()
    created = False
    product = find_product(db, validated)
    if product is None:
        source = db.scalar(select(DiscoverySource).where(DiscoverySource.connector_key == "user_submitted"))
        product = Product(
            id=uuid.uuid4(),
            product_url=validated.canonical_url,
            normalized_url=validated.normalized_url,
            original_url=validated.original_url,
            flipkart_pid=validated.pid,
            item_id=validated.item_id,
            source_id=source.id if source else None,
            submitted_by=user.id,
            first_seen_at=now,
        )
        db.add(product)
        try:
            db.flush()
            created = True
        except IntegrityError:
            db.rollback()
            product = find_product(db, validated)
            if product is None:
                raise
    elif product.archived_at is not None:
        product.archived_at = None

    if not settings.product_page_access_permitted:
        product.access_status = AccessStatus.NOT_PERMITTED
        product.last_access_error = NOT_PERMITTED_MESSAGE
    elif product.access_status == AccessStatus.NOT_PERMITTED:
        product.access_status = AccessStatus.PENDING
        product.last_access_error = None

    if monitor:
        ensure_monitored(db, product.id, user.id, get_app_config(db).scan_interval_minutes, now)
    db.commit()
    db.refresh(product)
    return product, created
