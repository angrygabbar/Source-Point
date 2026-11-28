import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import EventOutbox
from app.services.audit import jsonable


def emit(
    db: Session,
    institute_id: uuid.UUID | None,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID | None,
    payload: dict[str, Any] | None = None,
    dedupe_key: str | None = None,
) -> None:
    """Write an event in the caller's transaction; the worker dispatches side effects after commit."""
    stmt = insert(EventOutbox).values(
        id=uuid.uuid4(),
        institute_id=institute_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=jsonable(payload or {}),
        status="pending",
        attempts=0,
        available_at=datetime.now(timezone.utc),
        dedupe_key=dedupe_key,
    )
    if dedupe_key:
        stmt = stmt.on_conflict_do_nothing(index_elements=["dedupe_key"], index_where=EventOutbox.dedupe_key.isnot(None))
    db.execute(stmt)
