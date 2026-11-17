from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.models import PriceHistory, Product
from app.database.session import get_db
from app.services.clock import range_start

router = APIRouter(prefix="/api/price-history", tags=["price-history"], dependencies=[Depends(get_current_user)])


@router.get("/movements")
def movements(
    range: Literal["today", "7d", "30d", "90d"] = "7d",
    direction: Literal["all", "drop", "rise"] = "all",
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> dict:
    """Individual price changes between consecutive observations of the same product."""
    start = range_start(range)
    prev_price = func.lag(PriceHistory.selling_price).over(partition_by=PriceHistory.product_id, order_by=PriceHistory.captured_at)
    prev_seller = func.lag(PriceHistory.seller).over(partition_by=PriceHistory.product_id, order_by=PriceHistory.captured_at)
    ph = (
        select(PriceHistory.product_id, PriceHistory.captured_at, PriceHistory.selling_price, PriceHistory.seller,
               prev_price.label("prev_price"), prev_seller.label("prev_seller"))
        .where(PriceHistory.selling_price.is_not(None))
        .subquery()
    )
    stmt = (
        select(ph, Product.title, Product.brand, Product.category, Product.image_url)
        .join(Product, Product.id == ph.c.product_id)
        .where(ph.c.captured_at >= start, ph.c.prev_price.is_not(None), ph.c.selling_price != ph.c.prev_price,
               Product.archived_at.is_(None))
    )
    if direction == "drop":
        stmt = stmt.where(ph.c.selling_price < ph.c.prev_price)
    elif direction == "rise":
        stmt = stmt.where(ph.c.selling_price > ph.c.prev_price)
    rows = db.execute(stmt.order_by(ph.c.captured_at.desc()).limit(limit)).all()
    data = []
    for r in rows:
        change = r.selling_price - r.prev_price
        data.append({
            "product_id": r.product_id, "title": r.title, "brand": r.brand, "category": r.category, "image_url": r.image_url,
            "captured_at": r.captured_at, "previous_price": r.prev_price, "new_price": r.selling_price,
            "change": change, "change_pct": round(change / r.prev_price * 100, 2) if r.prev_price else None,
            "seller": r.seller, "seller_changed": r.prev_seller is not None and r.seller != r.prev_seller,
        })
    return {"data": data}
