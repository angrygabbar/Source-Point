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
from models.commerce import (
    Invoice, InvoiceRefund,
    SupersCoinWallet, SupersCoinTransaction, SupersCoinInvoice,
    InventoryRollbackTerms, InventoryRollbackTermsDecision
)


REQUIRED_SUPERSCOINS_TABLES = [
    SupersCoinWallet.__table__,
    SupersCoinTransaction.__table__,
    SupersCoinInvoice.__table__,
]

REQUIRED_ROLLBACK_TERMS_TABLES = [
    InventoryRollbackTerms.__table__,
    InventoryRollbackTermsDecision.__table__,
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


def ensure_rollback_terms_tables():
    for table in REQUIRED_ROLLBACK_TERMS_TABLES:
        table.create(db.engine, checkfirst=True)

    existing_terms = InventoryRollbackTerms.query.filter_by(is_active=True).first()
    if not existing_terms:
        from services.rollback_terms_service import (
            DEFAULT_ROLLBACK_TERMS_CONTENT,
            DEFAULT_ROLLBACK_TERMS_TITLE,
        )

        latest_terms = InventoryRollbackTerms.query.order_by(InventoryRollbackTerms.version.desc()).first()
        next_version = (latest_terms.version + 1) if latest_terms else 1
        db.session.add(InventoryRollbackTerms(
            version=next_version,
            title=DEFAULT_ROLLBACK_TERMS_TITLE,
            content=DEFAULT_ROLLBACK_TERMS_CONTENT,
            is_active=True,
        ))

    db.session.commit()
    print("[schema] Rollback terms tables ready")


def ensure_invoice_refund_schema():
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    if Invoice.__tablename__ in table_names:
        invoice_columns = {column["name"] for column in inspector.get_columns(Invoice.__tablename__)}
        if "amount_refunded" not in invoice_columns:
            dialect = db.engine.dialect.name
            if dialect == "postgresql":
                sql = 'ALTER TABLE invoice ADD COLUMN IF NOT EXISTS amount_refunded NUMERIC(10, 2) NOT NULL DEFAULT 0.00'
            elif dialect == "sqlite":
                sql = 'ALTER TABLE invoice ADD COLUMN amount_refunded NUMERIC(10, 2) NOT NULL DEFAULT 0.00'
            else:
                sql = 'ALTER TABLE invoice ADD COLUMN amount_refunded NUMERIC(10, 2) NOT NULL DEFAULT 0.00'
            db.session.execute(text(sql))
            db.session.commit()
            print("[schema] Added invoice.amount_refunded")

    InvoiceRefund.__table__.create(db.engine, checkfirst=True)
    db.session.commit()
    print("[schema] Invoice refund tables ready")


def main():
    wait_for_database(app)
    with app.app_context():
        ensure_user_columns()
        ensure_superscoins_tables()
        ensure_rollback_terms_tables()
        ensure_invoice_refund_schema()


if __name__ == "__main__":
    main()
