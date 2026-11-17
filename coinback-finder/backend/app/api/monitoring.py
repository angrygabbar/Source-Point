from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, contains_eager

from app.api.deps import PageParams, get_current_user, page_params, page_response, paginate
from app.api.schemas import MonitorIn
from app.api.serializers import monitored_out
from app.database.models import MonitoredProduct, Product, User
from app.database.session import get_db
from app.services.monitoring import disable_monitoring, ensure_monitored
from app.services.settings_store import get_app_config

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_monitored(enabled: bool | None = True, params: PageParams = Depends(page_params), db: Session = Depends(get_db)) -> dict:
    stmt = (
        select(MonitoredProduct).join(Product, Product.id == MonitoredProduct.product_id)
        .options(contains_eager(MonitoredProduct.product)).where(Product.archived_at.is_(None))
    )
    if enabled is not None:
        stmt = stmt.where(MonitoredProduct.enabled.is_(enabled))
    rows, total = paginate(db, stmt.order_by(MonitoredProduct.next_due_at.asc().nulls_first()), params)
    return page_response([monitored_out(r[0]) for r in rows], total, params)


@router.post("/{product_id}")
def monitor(product_id: uuid.UUID, payload: MonitorIn | None = None, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)) -> dict:
    product = db.get(Product, product_id)
    if product is None or product.archived_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found.")
    frequency = (payload.frequency_minutes if payload else None) or get_app_config(db).scan_interval_minutes
    record = ensure_monitored(db, product_id, user.id, frequency)
    db.commit()
    db.refresh(record)
    return {"data": monitored_out(record)}


@router.delete("/{product_id}")
def unmonitor(product_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    if not disable_monitoring(db, product_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product is not monitored.")
    db.commit()
    return {"data": {"product_id": product_id, "enabled": False}}
