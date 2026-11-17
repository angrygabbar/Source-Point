from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.services import dashboard
from app.services.clock import IST, range_start, utcnow

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/summary")
def summary(db: Session = Depends(get_db)) -> dict:
    return {"data": dashboard.summary(db)}


@router.get("/panels")
def panels(db: Session = Depends(get_db)) -> dict:
    return {"data": dashboard.panels(db)}


@router.get("/scanner-status")
def scanner_status(db: Session = Depends(get_db)) -> dict:
    return {"data": dashboard.scanner_status(db)}


@router.get("/analytics")
def analytics(
    range: Literal["today", "7d", "30d", "90d", "custom"] = "30d",
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
) -> dict:
    now = utcnow()
    if range == "custom":
        if start is None or end is None or start > end:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Custom range requires valid 'from' and 'to' dates.")
        if (end - start).days > 366:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Custom range is limited to 366 days.")
        start_dt = datetime.combine(start, time.min, tzinfo=IST).astimezone(timezone.utc)
        end_dt = min(datetime.combine(end + timedelta(days=1), time.min, tzinfo=IST).astimezone(timezone.utc), now)
    else:
        start_dt, end_dt = range_start(range, now), now
    return {"data": dashboard.analytics(db, start_dt, end_dt)}
