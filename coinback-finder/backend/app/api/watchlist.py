from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.schemas import WatchlistIn
from app.api.serializers import offer_brief, product_row
from app.database.models import MonitoredProduct, Product, User, Watchlist
from app.database.session import get_db
from app.services.queries import best_offer_alias

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
def list_watchlist(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    bo = best_offer_alias()
    monitored = select(MonitoredProduct.id).where(MonitoredProduct.product_id == Product.id, MonitoredProduct.enabled.is_(True)).exists()
    rows = db.execute(
        select(Watchlist, Product, bo, monitored.label("m"))
        .join(Product, Product.id == Watchlist.product_id)
        .outerjoin(bo, bo.product_id == Product.id)
        .where(Watchlist.user_id == user.id, Product.archived_at.is_(None))
        .order_by(Watchlist.created_at.desc())
    ).all()
    data = []
    for w, p, offer, mon in rows:
        price_hit = w.target_price is not None and p.current_price is not None and p.current_price <= w.target_price
        pct_hit = (w.target_percentage is not None and offer is not None and offer.advertised_percentage is not None
                   and offer.advertised_percentage >= w.target_percentage)
        data.append({
            "id": w.id, "note": w.note, "target_price": w.target_price, "target_percentage": w.target_percentage,
            "created_at": w.created_at, "target_price_met": price_hit, "target_percentage_met": pct_hit,
            "product": product_row(p, offer, mon), "best_offer": offer_brief(offer),
        })
    return {"data": data}


@router.post("", status_code=status.HTTP_201_CREATED)
def add_to_watchlist(payload: WatchlistIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    product = db.get(Product, payload.product_id)
    if product is None or product.archived_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found.")
    values = payload.model_dump()
    stmt = insert(Watchlist).values(id=uuid.uuid4(), user_id=user.id, **values).on_conflict_do_update(
        constraint="uq_watchlists_user_product",
        set_={"note": values["note"], "target_price": values["target_price"], "target_percentage": values["target_percentage"]},
    )
    db.execute(stmt)
    db.commit()
    return {"data": {"product_id": payload.product_id, "saved": True}}


@router.delete("/{product_id}")
def remove_from_watchlist(product_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    result = db.execute(delete(Watchlist).where(Watchlist.user_id == user.id, Watchlist.product_id == product_id))
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product is not on the watchlist.")
    return {"data": {"product_id": product_id, "saved": False}}
