from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import PageParams, csv_list, get_current_user, page_params, page_response, paginate
from app.api.schemas import ManualOfferIn, ProductSubmitIn, ProductUpdateIn
from app.api.serializers import offer_full, price_point, product_row, snapshot_out, verification_out
from app.database.enums import AccessStatus, OfferStatus, SourceType
from app.database.models import (
    ManualVerification,
    MonitoredProduct,
    Offer,
    OfferSnapshot,
    PriceHistory,
    Product,
    User,
    Watchlist,
)
from app.database.session import get_db
from app.discovery.service import submit_product_url
from app.discovery.url_validation import UrlValidationError
from app.services.clock import range_start, utcnow
from app.services.export import export_csv, export_xlsx
from app.services.ingestion import compute_discount, record_price, upsert_offers
from app.services.monitoring import disable_monitoring
from app.services.offer_math import recompute_offer
from app.services.queries import ProductFilters, product_query
from app.services.settings_store import get_app_config

router = APIRouter(prefix="/api/products", tags=["products"], dependencies=[Depends(get_current_user)])

OFFER_STATUSES = {s.value for s in OfferStatus}
SOURCE_TYPES = {s.value for s in SourceType}
ACCESS_STATUSES = {s.value for s in AccessStatus}
EXPORT_LIMIT = 10000


def product_filters(
    q: str | None = Query(None, max_length=200),
    category: str | None = Query(None, max_length=255),
    brand: str | None = Query(None, max_length=255),
    seller: str | None = Query(None, max_length=255),
    min_price: Decimal | None = Query(None, ge=0),
    max_price: Decimal | None = Query(None, ge=0),
    min_pct: Decimal | None = Query(None, ge=0, le=1000),
    max_pct: Decimal | None = Query(None, ge=0, le=1000),
    status_: str | None = Query(None, alias="status", max_length=300),
    source_type: str | None = Query(None, max_length=300),
    access_status: str | None = Query(None, max_length=300),
    has_offer: bool | None = None,
    monitored: bool | None = None,
) -> ProductFilters:
    return ProductFilters(
        q=q or None, category=category or None, brand=brand or None, seller=seller or None,
        min_price=min_price, max_price=max_price, min_pct=min_pct, max_pct=max_pct,
        statuses=csv_list(status_, OFFER_STATUSES), source_types=csv_list(source_type, SOURCE_TYPES),
        access_statuses=csv_list(access_status, ACCESS_STATUSES), has_offer=has_offer, monitored=monitored,
    )


def _get_product(db: Session, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.archived_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found.")
    return product


@router.get("")
def list_products(
    filters: ProductFilters = Depends(product_filters),
    sort: str | None = Query(None, max_length=32),
    order: Literal["asc", "desc"] = "desc",
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
) -> dict:
    rows, total = paginate(db, product_query(filters, sort, order), params)
    return page_response([product_row(p, bo, mon) for p, bo, mon in rows], total, params)


@router.get("/facets")
def facets(db: Session = Depends(get_db)) -> dict:
    def distinct(column):
        return [
            {"value": v, "count": int(c)}
            for v, c in db.execute(
                select(column, func.count()).where(Product.archived_at.is_(None), column.is_not(None))
                .group_by(column).order_by(func.count().desc()).limit(200)
            ).all()
        ]

    price = db.execute(select(func.min(Product.current_price), func.max(Product.current_price)).where(Product.archived_at.is_(None))).one()
    return {"data": {
        "categories": distinct(Product.category),
        "brands": distinct(Product.brand),
        "sellers": distinct(Product.seller),
        "price_range": {"min": price[0], "max": price[1]},
    }}


@router.get("/export")
def export_products(
    format: Literal["csv", "xlsx"] = "csv",
    filters: ProductFilters = Depends(product_filters),
    sort: str | None = Query(None, max_length=32),
    order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
) -> Response:
    rows = db.execute(product_query(filters, sort, order).limit(EXPORT_LIMIT)).all()
    columns = [
        ("Title", lambda r: r[0].title),
        ("Brand", lambda r: r[0].brand),
        ("Category", lambda r: r[0].category),
        ("Flipkart PID", lambda r: r[0].flipkart_pid),
        ("Selling price (INR)", lambda r: r[0].current_price),
        ("MRP (INR)", lambda r: r[0].mrp),
        ("Discount %", lambda r: r[0].discount_percent),
        ("Advertised coins", lambda r: r[1].advertised_coins if r[1] else None),
        ("Estimated coins", lambda r: r[1].estimated_coins if r[1] else None),
        ("Advertised CoinBack %", lambda r: r[1].advertised_percentage if r[1] else None),
        ("Up to (conditional)", lambda r: r[1].is_up_to if r[1] else None),
        ("Max reward (coins)", lambda r: r[1].reward_cap_coins if r[1] else None),
        ("Seller", lambda r: r[0].seller),
        ("Verification status", lambda r: r[1].status if r[1] else None),
        ("Evidence source", lambda r: r[1].source_type if r[1] else None),
        ("Monitored", lambda r: r[2]),
        ("Last checked", lambda r: r[0].last_checked_at),
        ("First seen", lambda r: r[0].first_seen_at),
        ("Product URL", lambda r: r[0].product_url),
    ]
    stamp = utcnow().strftime("%Y%m%d-%H%M")
    if format == "xlsx":
        body = export_xlsx(columns, rows, "Products")
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        body = export_csv(columns, rows)
        media = "text/csv; charset=utf-8"
    return Response(body, media_type=media, headers={"Content-Disposition": f'attachment; filename="coinback-products-{stamp}.{format}"'})


@router.get("/intelligence")
def intelligence(
    filters: ProductFilters = Depends(product_filters),
    sort: str | None = Query(None, max_length=32),
    order: Literal["asc", "desc"] = "desc",
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
) -> dict:
    rows, total = paginate(db, product_query(filters, sort, order), params)
    ids = [p.id for p, _, _ in rows]
    stats: dict = {}
    if ids:
        week_ago = utcnow() - timedelta(days=7)
        for pid, lo, hi, avg, n, sellers in db.execute(
            select(PriceHistory.product_id, func.min(PriceHistory.selling_price), func.max(PriceHistory.selling_price),
                   func.avg(PriceHistory.selling_price), func.count(), func.count(func.distinct(PriceHistory.seller)))
            .where(PriceHistory.product_id.in_(ids)).group_by(PriceHistory.product_id)
        ).all():
            stats[pid] = {"lowest_price": lo, "highest_price": hi, "average_price": round(avg, 2) if avg is not None else None,
                          "observations": int(n), "distinct_sellers": int(sellers)}
        ranked = (
            select(PriceHistory.product_id, PriceHistory.selling_price,
                   func.row_number().over(partition_by=PriceHistory.product_id, order_by=PriceHistory.captured_at.desc()).label("rn"))
            .where(PriceHistory.product_id.in_(ids), PriceHistory.captured_at <= week_ago)
            .subquery()
        )
        for pid, price in db.execute(select(ranked.c.product_id, ranked.c.selling_price).where(ranked.c.rn == 1)).all():
            stats.setdefault(pid, {})["price_7d_ago"] = price
        offer_counts = dict(db.execute(
            select(Offer.product_id, func.count()).where(Offer.product_id.in_(ids)).group_by(Offer.product_id)
        ).all())
    data = []
    for p, bo, mon in rows:
        s = stats.get(p.id, {})
        prev = s.get("price_7d_ago")
        change = None
        if prev and p.current_price is not None and prev > 0:
            change = round((p.current_price - prev) / prev * 100, 2)
        data.append({**product_row(p, bo, mon), "price_stats": {**s, "change_7d_pct": change},
                     "offer_count": int(offer_counts.get(p.id, 0)) if ids else 0})
    return page_response(data, total, params)


@router.get("/compare")
def compare(ids: str = Query(..., max_length=200), db: Session = Depends(get_db)) -> dict:
    try:
        id_list = list(dict.fromkeys(uuid.UUID(i.strip()) for i in ids.split(",") if i.strip()))
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid product id.") from exc
    if not 1 <= len(id_list) <= 4:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Select between one and four products.")
    rows = db.execute(product_query(ProductFilters(ids=id_list), None, "desc")).all()
    lows = dict(db.execute(
        select(PriceHistory.product_id, func.min(PriceHistory.selling_price)).where(PriceHistory.product_id.in_(id_list))
        .group_by(PriceHistory.product_id)
    ).all())
    out = []
    for p, bo, mon in rows:
        full = offer_full(bo, include_product=False) if bo else None
        out.append({**product_row(p, bo, mon), "historical_low": lows.get(p.id), "best_offer_detail": full})
    order_index = {pid: i for i, pid in enumerate(id_list)}
    out.sort(key=lambda r: order_index.get(r["id"], 99))
    return {"data": out}


@router.get("/{product_id}")
def get_product(product_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    product = _get_product(db, product_id)
    offers = db.scalars(select(Offer).where(Offer.product_id == product_id).order_by(Offer.last_seen_at.desc())).all()
    monitored = db.scalar(select(MonitoredProduct).where(MonitoredProduct.product_id == product_id))
    watch = db.scalar(select(Watchlist).where(Watchlist.product_id == product_id, Watchlist.user_id == user.id))
    stats = db.execute(
        select(func.min(PriceHistory.selling_price), func.max(PriceHistory.selling_price), func.avg(PriceHistory.selling_price),
               func.count(), func.min(PriceHistory.captured_at), func.max(PriceHistory.captured_at))
        .where(PriceHistory.product_id == product_id)
    ).one()
    sellers = [
        {"seller": s, "first_seen": first, "last_seen": last, "observations": int(n)}
        for s, first, last, n in db.execute(
            select(PriceHistory.seller, func.min(PriceHistory.captured_at), func.max(PriceHistory.captured_at), func.count())
            .where(PriceHistory.product_id == product_id, PriceHistory.seller.is_not(None))
            .group_by(PriceHistory.seller).order_by(func.min(PriceHistory.captured_at))
        ).all()
    ]
    verifications = db.execute(
        select(ManualVerification, User.username).outerjoin(User, User.id == ManualVerification.verified_by)
        .where(ManualVerification.product_id == product_id).order_by(ManualVerification.verified_at.desc()).limit(100)
    ).all()
    best = next((o for o in sorted(
        (o for o in offers if o.status not in (OfferStatus.REJECTED, OfferStatus.EXPIRED, OfferStatus.SOURCE_UNAVAILABLE)),
        key=lambda o: (o.advertised_percentage is not None, o.advertised_percentage or 0, o.estimated_coins or 0), reverse=True,
    )), None)
    config = get_app_config(db)
    return {"data": {
        "product": product_row(product, best, bool(monitored and monitored.enabled)),
        "offers": [offer_full(o, include_product=False) for o in offers],
        "price_stats": {
            "lowest": stats[0], "highest": stats[1], "average": round(stats[2], 2) if stats[2] is not None else None,
            "observations": int(stats[3]), "first_recorded": stats[4], "last_recorded": stats[5],
        },
        "sellers": sellers,
        "verifications": [verification_out(v, name) for v, name in verifications],
        "monitoring": {
            "enabled": bool(monitored and monitored.enabled),
            "frequency_minutes": monitored.frequency_minutes if monitored else None,
            "last_processed_at": monitored.last_processed_at if monitored else None,
            "next_due_at": monitored.next_due_at if monitored else None,
        },
        "watchlist": {"saved": watch is not None, "note": watch.note if watch else None,
                      "target_price": watch.target_price if watch else None,
                      "target_percentage": watch.target_percentage if watch else None},
        "assumptions": {"supercoin_value_inr": config.supercoin_value_inr},
    }}


@router.get("/{product_id}/price-history")
def price_history(product_id: uuid.UUID, range: str = Query("90d", pattern="^(today|7d|30d|90d|365d|all)$"),
                  db: Session = Depends(get_db)) -> dict:
    _get_product(db, product_id)
    stmt = select(PriceHistory).where(PriceHistory.product_id == product_id)
    if range != "all":
        stmt = stmt.where(PriceHistory.captured_at >= range_start(range))
    rows = db.scalars(stmt.order_by(PriceHistory.captured_at).limit(5000)).all()
    return {"data": [price_point(r) for r in rows]}


@router.get("/{product_id}/offer-history")
def offer_history(product_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_product(db, product_id)
    rows = db.scalars(
        select(OfferSnapshot).where(OfferSnapshot.product_id == product_id).order_by(OfferSnapshot.captured_at.desc()).limit(1000)
    ).all()
    return {"data": [snapshot_out(s) for s in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_product(payload: ProductSubmitIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    try:
        product, created = submit_product_url(db, payload.url, user=user, monitor=payload.monitor)
    except UrlValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    monitored = db.scalar(select(MonitoredProduct.enabled).where(MonitoredProduct.product_id == product.id))
    return {"data": {**product_row(product, None, bool(monitored)), "created": created}}


@router.patch("/{product_id}")
def update_product(product_id: uuid.UUID, payload: ProductUpdateIn, db: Session = Depends(get_db)) -> dict:
    product = _get_product(db, product_id)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(product, key, value)
    price_fields = {"current_price", "mrp", "shipping_charge", "seller", "in_stock"}
    now = utcnow()
    if price_fields & changes.keys():
        product.discount_percent = compute_discount(product.current_price, product.mrp)
        db.flush()
        record_price(db, product, SourceType.MANUAL, now, 0)
        coin_value = get_app_config(db).coin_value
        for offer in db.scalars(select(Offer).where(Offer.product_id == product_id)).all():
            recompute_offer(offer, product.current_price, coin_value)
    db.commit()
    db.refresh(product)
    return {"data": product_row(product)}


@router.post("/{product_id}/offers", status_code=status.HTTP_201_CREATED)
def add_manual_offer(product_id: uuid.UUID, payload: ManualOfferIn, db: Session = Depends(get_db)) -> dict:
    product = _get_product(db, product_id)
    outcome = upsert_offers(
        db, product, [payload.text], source=None, source_type=SourceType.MANUAL, source_url=product.product_url,
        extra={"entered_by": "operator"}, config=get_app_config(db), now=utcnow(),
    )
    db.commit()
    if not outcome.new_offer_ids and not outcome.changed_offer_ids and outcome.offers_detected == 0:
        detail = "Text classified as not a CoinBack offer." if outcome.non_coinback else "No SuperCoin reward statement recognised in the text."
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail)
    ids = outcome.new_offer_ids + outcome.changed_offer_ids
    offers = db.scalars(select(Offer).where(Offer.id.in_(ids))).all() if ids else []
    return {"data": {"created": len(outcome.new_offer_ids), "updated": len(outcome.changed_offer_ids),
                     "offers": [offer_full(o, include_product=False) for o in offers]}}


@router.delete("/{product_id}")
def archive_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    product = _get_product(db, product_id)
    product.archived_at = utcnow()
    disable_monitoring(db, product_id)
    db.commit()
    return {"data": {"archived": True, "id": product_id}}
