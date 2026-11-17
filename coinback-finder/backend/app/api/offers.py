from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import PageParams, csv_list, get_current_user, page_params, page_response, paginate
from app.api.schemas import RejectIn, VerifyIn
from app.api.serializers import offer_full, snapshot_out, verification_out
from app.database.enums import OfferStatus, RewardType, SourceType, VerificationStatus
from app.database.models import ManualVerification, Offer, OfferSnapshot, User
from app.database.session import get_db
from app.services.clock import range_start, utcnow
from app.services.export import export_csv, export_xlsx
from app.services.queries import OfferFilters, offer_query
from app.verification.service import VerificationInput, record_verification

router = APIRouter(prefix="/api/offers", tags=["offers"], dependencies=[Depends(get_current_user)])

OFFER_STATUSES = {s.value for s in OfferStatus}
REWARD_TYPES = {r.value for r in RewardType}
SOURCE_TYPES = {s.value for s in SourceType}


def offer_filters(
    q: str | None = Query(None, max_length=200),
    status_: str | None = Query(None, alias="status", max_length=300),
    reward_type: str | None = Query(None, max_length=300),
    source_type: str | None = Query(None, max_length=300),
    min_pct: Decimal | None = Query(None, ge=0, le=1000),
    max_pct: Decimal | None = Query(None, ge=0, le=1000),
    pct_mode: Literal["exact_100", "above_100", "gte_100"] | None = None,
    capped: bool | None = None,
    verified: bool | None = None,
    up_to: bool | None = None,
    min_coins: int | None = Query(None, ge=0),
    min_price: Decimal | None = Query(None, ge=0),
    max_price: Decimal | None = Query(None, ge=0),
    category: str | None = Query(None, max_length=255),
    include_inactive: bool = False,
    detected: Literal["today", "7d", "30d", "90d"] | None = None,
) -> OfferFilters:
    return OfferFilters(
        q=q or None, statuses=csv_list(status_, OFFER_STATUSES), reward_types=csv_list(reward_type, REWARD_TYPES),
        source_types=csv_list(source_type, SOURCE_TYPES), min_pct=min_pct, max_pct=max_pct, pct_mode=pct_mode,
        capped=capped, verified=verified, up_to=up_to, min_coins=min_coins, min_price=min_price, max_price=max_price,
        category=category or None, active_only=not include_inactive,
        detected_since=range_start(detected) if detected else None,
    )


def _list(db: Session, filters: OfferFilters, sort: str | None, order: str, params: PageParams) -> dict:
    rows, total = paginate(db, offer_query(filters, sort, order), params)
    return page_response([offer_full(r[0]) for r in rows], total, params)


SortParam = Query(None, max_length=32)


@router.get("")
def list_offers(filters: OfferFilters = Depends(offer_filters), sort: str | None = SortParam,
                order: Literal["asc", "desc"] = "desc", params: PageParams = Depends(page_params),
                db: Session = Depends(get_db)) -> dict:
    return _list(db, filters, sort, order, params)


@router.get("/100-percent")
def hundred_percent(filters: OfferFilters = Depends(offer_filters), sort: str | None = SortParam,
                    order: Literal["asc", "desc"] = "desc", params: PageParams = Depends(page_params),
                    db: Session = Depends(get_db)) -> dict:
    filters.pct_mode = filters.pct_mode or "gte_100"
    return _list(db, filters, sort or "pct", order, params)


@router.get("/verified")
def verified_offers(filters: OfferFilters = Depends(offer_filters), sort: str | None = SortParam,
                    order: Literal["asc", "desc"] = "desc", params: PageParams = Depends(page_params),
                    db: Session = Depends(get_db)) -> dict:
    filters.verified = True
    return _list(db, filters, sort, order, params)


@router.get("/active")
def active_offers(filters: OfferFilters = Depends(offer_filters), sort: str | None = SortParam,
                  order: Literal["asc", "desc"] = "desc", params: PageParams = Depends(page_params),
                  db: Session = Depends(get_db)) -> dict:
    filters.active_only = True
    return _list(db, filters, sort, order, params)


@router.get("/export")
def export_offers(format: Literal["csv", "xlsx"] = "csv", filters: OfferFilters = Depends(offer_filters),
                  sort: str | None = SortParam, order: Literal["asc", "desc"] = "desc",
                  db: Session = Depends(get_db)) -> Response:
    offers = [r[0] for r in db.execute(offer_query(filters, sort, order).limit(10000)).all()]
    columns = [
        ("Product", lambda o: o.product.title),
        ("Brand", lambda o: o.product.brand),
        ("Category", lambda o: o.product.category),
        ("Selling price (INR)", lambda o: o.product.current_price),
        ("Offer", lambda o: o.title),
        ("Reward type", lambda o: o.reward_type),
        ("Up to (conditional)", lambda o: o.is_up_to),
        ("Advertised CoinBack %", lambda o: o.advertised_percentage),
        ("Advertised coins", lambda o: o.advertised_coins),
        ("Estimated coins", lambda o: o.estimated_coins),
        ("Max reward (coins)", lambda o: o.reward_cap_coins),
        ("Est. redemption value (INR)", lambda o: o.estimated_redemption_value),
        ("Est. effective cost (INR)", lambda o: o.effective_cost_estimate),
        ("Status", lambda o: o.status),
        ("Confidence", lambda o: o.confidence),
        ("Evidence source", lambda o: o.source_type),
        ("Valid until", lambda o: o.valid_until),
        ("First detected", lambda o: o.first_detected_at),
        ("Last seen", lambda o: o.last_seen_at),
        ("Classification reason", lambda o: o.classification_reason),
        ("Product URL", lambda o: o.product.product_url),
    ]
    stamp = utcnow().strftime("%Y%m%d-%H%M")
    if format == "xlsx":
        body, media = export_xlsx(columns, offers, "Offers"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        body, media = export_csv(columns, offers), "text/csv; charset=utf-8"
    return Response(body, media_type=media, headers={"Content-Disposition": f'attachment; filename="coinback-offers-{stamp}.{format}"'})


def _get_offer(db: Session, offer_id: uuid.UUID) -> Offer:
    offer = db.get(Offer, offer_id)
    if offer is None or offer.product.archived_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer not found.")
    return offer


@router.get("/{offer_id}")
def get_offer(offer_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return {"data": offer_full(_get_offer(db, offer_id))}


@router.get("/{offer_id}/history")
def offer_history(offer_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    _get_offer(db, offer_id)
    snapshots = db.scalars(select(OfferSnapshot).where(OfferSnapshot.offer_id == offer_id).order_by(OfferSnapshot.captured_at.desc()).limit(500)).all()
    verifications = db.execute(
        select(ManualVerification, User.username).outerjoin(User, User.id == ManualVerification.verified_by)
        .where(ManualVerification.offer_id == offer_id).order_by(ManualVerification.verified_at.desc())
    ).all()
    return {"data": {"snapshots": [snapshot_out(s) for s in snapshots],
                     "verifications": [verification_out(v, u) for v, u in verifications]}}


@router.post("/{offer_id}/verify")
def verify(offer_id: uuid.UUID, payload: VerifyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    offer = _get_offer(db, offer_id)
    record = record_verification(db, offer, VerificationInput(**payload.model_dump()), user)
    db.refresh(offer)
    return {"data": {"offer": offer_full(offer), "verification": verification_out(record, user.username)}}


@router.post("/{offer_id}/reject")
def reject(offer_id: uuid.UUID, payload: RejectIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    offer = _get_offer(db, offer_id)
    record = record_verification(db, offer, VerificationInput(status=VerificationStatus.REJECTED, notes=payload.notes), user)
    db.refresh(offer)
    return {"data": {"offer": offer_full(offer), "verification": verification_out(record, user.username)}}
