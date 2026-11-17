from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, like_pattern
from app.api.schemas import SavedFilterIn, SettingsIn
from app.config import get_settings
from app.database.models import Offer, Product, SavedFilter, User
from app.database.session import get_db
from app.services.offer_math import recompute_offer
from app.services.settings_store import get_app_config, update_app_config

router = APIRouter(prefix="/api", tags=["settings"])


def _settings_out(db: Session) -> dict:
    s = get_settings()
    return {
        **get_app_config(db).as_dict(),
        "display_timezone": s.display_timezone,
        "currency": s.currency,
        "environment": {
            "product_page_fetch_enabled": s.product_page_fetch_enabled,
            "product_page_permission_confirmed": s.product_page_permission_confirmed,
            "google_cse_configured": bool(s.google_cse_api_key and s.google_cse_engine_id),
            "brave_search_configured": bool(s.brave_search_api_key),
            "telegram_configured": s.telegram_configured,
            "telegram_dry_run": s.telegram_dry_run or not s.telegram_bot_token,
            "telegram_commands_enabled": s.telegram_commands_enabled,
            "flipkart_allowed_hosts": s.flipkart_host_list,
            "third_party_allowed_hosts": s.third_party_host_list,
            "cookie_secure": s.cookie_secure,
        },
    }


@router.get("/settings")
def read_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"data": _settings_out(db)}


@router.put("/settings")
def write_settings(payload: SettingsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    changes = payload.model_dump(exclude_unset=True, exclude={"clear_supercoin_value"})
    changes = {k: v for k, v in changes.items() if v is not None}
    if payload.clear_supercoin_value:
        changes["supercoin_value_inr"] = None
    before = get_app_config(db).supercoin_value_inr
    config = update_app_config(db, changes)
    if config.supercoin_value_inr != before:
        # Re-derive labelled estimates so they reflect the new conversion assumption.
        for offer in db.scalars(select(Offer).join(Product, Product.id == Offer.product_id)).all():
            recompute_offer(offer, offer.product.current_price, config.coin_value)
    db.commit()
    return {"data": _settings_out(db)}


@router.get("/saved-filters")
def list_saved_filters(page: str = Query(..., max_length=64), user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(SavedFilter).where(SavedFilter.user_id == user.id, SavedFilter.page == page).order_by(SavedFilter.name)).all()
    return {"data": [{"id": r.id, "name": r.name, "page": r.page, "params": r.params, "created_at": r.created_at} for r in rows]}


@router.post("/saved-filters", status_code=status.HTTP_201_CREATED)
def save_filter(payload: SavedFilterIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    stmt = insert(SavedFilter).values(id=uuid.uuid4(), user_id=user.id, page=payload.page, name=payload.name, params=payload.params)
    stmt = stmt.on_conflict_do_update(constraint="uq_saved_filters_user_page_name", set_={"params": payload.params})
    db.execute(stmt)
    db.commit()
    row = db.scalar(select(SavedFilter).where(SavedFilter.user_id == user.id, SavedFilter.page == payload.page, SavedFilter.name == payload.name))
    return {"data": {"id": row.id, "name": row.name, "page": row.page, "params": row.params, "created_at": row.created_at}}


@router.delete("/saved-filters/{filter_id}")
def delete_filter(filter_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    result = db.execute(delete(SavedFilter).where(SavedFilter.id == filter_id, SavedFilter.user_id == user.id))
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Saved filter not found.")
    return {"data": {"deleted": True}}


@router.get("/search")
def global_search(q: str = Query(..., min_length=2, max_length=200), user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> dict:
    pattern = like_pattern(q.strip())
    products = db.execute(
        select(Product.id, Product.title, Product.brand, Product.category, Product.current_price, Product.image_url)
        .where(Product.archived_at.is_(None), or_(Product.title.ilike(pattern, escape="\\"), Product.brand.ilike(pattern, escape="\\"),
                                                  Product.flipkart_pid.ilike(pattern, escape="\\")))
        .order_by(Product.last_seen_at.desc().nulls_last()).limit(8)
    ).all()
    categories = db.execute(
        select(Product.category, func.count()).where(Product.archived_at.is_(None), Product.category.ilike(pattern, escape="\\"))
        .group_by(Product.category).limit(5)
    ).all()
    return {"data": {
        "products": [{"id": r.id, "title": r.title, "brand": r.brand, "category": r.category, "current_price": r.current_price,
                      "image_url": r.image_url} for r in products],
        "categories": [{"value": c, "count": int(n)} for c, n in categories],
    }}
