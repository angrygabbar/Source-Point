from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.models import MonitoredProduct
from app.services.clock import utcnow


def ensure_monitored(db: Session, product_id: uuid.UUID, user_id: uuid.UUID | None, frequency_minutes: int,
                     now: datetime | None = None) -> MonitoredProduct:
    now = now or utcnow()
    stmt = (
        insert(MonitoredProduct)
        .values(id=uuid.uuid4(), product_id=product_id, enabled=True, frequency_minutes=frequency_minutes,
                created_by=user_id, next_due_at=now)
        .on_conflict_do_update(
            index_elements=[MonitoredProduct.product_id],
            set_={"enabled": True, "frequency_minutes": frequency_minutes, "next_due_at": now},
        )
    )
    db.execute(stmt)
    db.flush()
    return db.scalar(select(MonitoredProduct).where(MonitoredProduct.product_id == product_id))


def disable_monitoring(db: Session, product_id: uuid.UUID) -> bool:
    result = db.execute(
        update(MonitoredProduct).where(MonitoredProduct.product_id == product_id).values(enabled=False)
    )
    return result.rowcount > 0
