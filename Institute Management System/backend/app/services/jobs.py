"""Background job helpers (exports/imports) shared by the API and the worker."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import BackgroundJob


def enqueue_export(db: Session, p, resource: str, fmt: str, params: dict[str, Any]) -> BackgroundJob:
    job = BackgroundJob(
        institute_id=p.institute_id,
        job_type="export",
        status="queued",
        params={"resource": resource, "format": fmt, "filters": params, "user_id": str(p.user_id) if p.user_id else None,
                "branch_id": str(p.selected_branch_id) if p.selected_branch_id else None},
        created_by_id=p.user_id,
    )
    db.add(job)
    db.flush()
    db.commit()
    from app.workers.tasks import run_export

    run_export.delay(str(job.id))
    return job


def job_owner_ok(job: BackgroundJob, p) -> bool:
    return job.institute_id == p.institute_id and (job.created_by_id == p.user_id or p.can("imports.read"))


def new_id() -> uuid.UUID:
    return uuid.uuid4()
