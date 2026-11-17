from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text

from app.database.session import engine

SCAN_LOCK_KEY = 0x43424B46  # "CBKF"


@contextmanager
def advisory_lock(key: int = SCAN_LOCK_KEY) -> Iterator[bool]:
    """Session-level PostgreSQL advisory lock; released automatically if the process dies."""
    conn = engine.connect()
    acquired = False
    try:
        acquired = bool(conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar())
        conn.commit()
        yield acquired
    finally:
        if acquired:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
            conn.commit()
        conn.close()
