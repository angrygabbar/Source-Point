import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Institute, NumberSequence


def financial_year_label(d: date, start_month: int = 4) -> str:
    start_year = d.year if d.month >= start_month else d.year - 1
    if start_month == 1:
        return str(start_year)
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def next_number(db: Session, institute_id: uuid.UUID, kind: str, prefix: str | None = None, on: date | None = None) -> str:
    """Gap-free, concurrency-safe document numbering per institute, kind and financial year."""
    inst = db.get(Institute, institute_id)
    fy = financial_year_label(on or date.today(), inst.financial_year_start_month if inst else 4)
    key = f"{kind}:{fy}"
    db.execute(
        insert(NumberSequence)
        .values(id=uuid.uuid4(), institute_id=institute_id, key=key, next_value=1)
        .on_conflict_do_nothing(index_elements=["institute_id", "key"])
    )
    seq = db.scalar(
        select(NumberSequence).where(NumberSequence.institute_id == institute_id, NumberSequence.key == key).with_for_update()
    )
    value = seq.next_value
    seq.next_value = value + 1
    db.flush()
    pfx = prefix or kind.upper()
    return f"{pfx}/{fy}/{value:05d}"


def next_code(db: Session, institute_id: uuid.UUID, kind: str, prefix: str, width: int = 5) -> str:
    """Simple non-financial running code, e.g. STU00001."""
    db.execute(
        insert(NumberSequence)
        .values(id=uuid.uuid4(), institute_id=institute_id, key=f"code:{kind}", next_value=1)
        .on_conflict_do_nothing(index_elements=["institute_id", "key"])
    )
    seq = db.scalar(
        select(NumberSequence)
        .where(NumberSequence.institute_id == institute_id, NumberSequence.key == f"code:{kind}")
        .with_for_update()
    )
    value = seq.next_value
    seq.next_value = value + 1
    db.flush()
    return f"{prefix}{value:0{width}d}"
