import time
import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app
from extensions import db
from models.auth import User
from models.commerce import SupersCoinWallet, SupersCoinTransaction, SupersCoinInvoice


REQUIRED_SUPERSCOINS_TABLES = [
    SupersCoinWallet.__table__,
    SupersCoinTransaction.__table__,
    SupersCoinInvoice.__table__,
]


def wait_for_database(app, attempts=30, delay=2):
    with app.app_context():
        for attempt in range(1, attempts + 1):
            try:
                db.session.execute(text("SELECT 1"))
                db.session.rollback()
                return
            except OperationalError as exc:
                db.session.rollback()
                if attempt == attempts:
                    raise
                print(f"[schema] Database not ready ({attempt}/{attempts}): {exc}")
                time.sleep(delay)


def ensure_user_columns():
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if User.__tablename__ not in table_names:
        return

    user_columns = {column["name"] for column in inspector.get_columns(User.__tablename__)}
    if "newsletter_subscribed" in user_columns:
        return

    dialect = db.engine.dialect.name
    if dialect == "postgresql":
        sql = 'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS newsletter_subscribed BOOLEAN NOT NULL DEFAULT TRUE'
    elif dialect == "sqlite":
        sql = 'ALTER TABLE "user" ADD COLUMN newsletter_subscribed BOOLEAN NOT NULL DEFAULT 1'
    else:
        sql = 'ALTER TABLE "user" ADD COLUMN newsletter_subscribed BOOLEAN NOT NULL DEFAULT TRUE'

    db.session.execute(text(sql))
    db.session.commit()
    print("[schema] Added user.newsletter_subscribed")


def ensure_superscoins_tables():
    for table in REQUIRED_SUPERSCOINS_TABLES:
        table.create(db.engine, checkfirst=True)
    db.session.commit()
    print("[schema] SupersCoins tables ready")


def main():
    wait_for_database(app)
    with app.app_context():
        ensure_user_columns()
        ensure_superscoins_tables()


if __name__ == "__main__":
    main()
