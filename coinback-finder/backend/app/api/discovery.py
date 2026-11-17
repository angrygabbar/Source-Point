from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import PageParams, csv_list, get_current_user, page_params, page_response, paginate
from app.api.schemas import DiscoveryRunIn, SourceUpdateIn
from app.api.serializers import scan_run_out, source_out
from app.database.enums import ScanStatus, ScanTrigger
from app.database.models import DiscoverySource, ScanRun, User
from app.database.session import get_db

router = APIRouter(prefix="/api/discovery", tags=["discovery"], dependencies=[Depends(get_current_user)])
SCAN_STATUSES = {s.value for s in ScanStatus}


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def run_discovery(payload: DiscoveryRunIn | None = None, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> dict:
    source_id = payload.source_id if payload else None
    if source_id and db.get(DiscoverySource, source_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found.")
    same_scope = ScanRun.source_id.is_(None) if source_id is None else ScanRun.source_id == source_id
    pending = db.scalar(select(ScanRun).where(ScanRun.status == ScanStatus.QUEUED, same_scope).limit(1))
    if pending:
        return {"data": {**scan_run_out(pending), "already_queued": True}}
    run = ScanRun(trigger=ScanTrigger.MANUAL, status=ScanStatus.QUEUED, source_id=source_id, requested_by=user.id)
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"data": {**scan_run_out(run), "already_queued": False}}


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)) -> dict:
    return {"data": [source_out(s) for s in db.scalars(select(DiscoverySource).order_by(DiscoverySource.name)).all()]}


@router.patch("/sources/{source_id}")
def update_source(source_id: uuid.UUID, payload: SourceUpdateIn, db: Session = Depends(get_db)) -> dict:
    source = db.get(DiscoverySource, source_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "enabled" in changes:
        source.enabled = changes["enabled"]
        if source.enabled:
            source.backoff_until = None
            source.consecutive_failures = 0
    if "rate_limit_per_minute" in changes:
        source.rate_limit_per_minute = changes["rate_limit_per_minute"]

    config = dict(source.config or {})
    mapping = {"phrases": "phrases", "categories": "categories", "max_queries_per_run": "max_queries_per_run",
               "results_per_query": "results_per_query", "feed_url": "url", "api_key_env": "api_key_env",
               "provider_name": "provider_name"}
    for field, key in mapping.items():
        if field in changes:
            if field == "feed_url" and changes[field] and not str(changes[field]).startswith("https://"):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Feed URL must use https.")
            config[key] = changes[field]
    source.config = config
    db.commit()
    db.refresh(source)
    return {"data": source_out(source)}


@router.get("/runs")
def list_runs(status_: str | None = Query(None, alias="status", max_length=200), params: PageParams = Depends(page_params),
              db: Session = Depends(get_db)) -> dict:
    stmt = select(ScanRun)
    statuses = csv_list(status_, SCAN_STATUSES)
    if statuses:
        stmt = stmt.where(ScanRun.status.in_(statuses))
    rows, total = paginate(db, stmt.order_by(ScanRun.queued_at.desc()), params)
    return page_response([scan_run_out(r[0]) for r in rows], total, params)


@router.get("/runs/{run_id}")
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    run = db.get(ScanRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan run not found.")
    return {"data": scan_run_out(run, include_details=True)}
