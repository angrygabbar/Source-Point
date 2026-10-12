import time
import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.schema import CreateColumn

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import app
from extensions import db
from models.auth import User
from models.asset import Asset
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

ASSET_EXTRA_COLUMNS = [
    Asset.__table__.c.asset_action,
    Asset.__table__.c.processor,
    Asset.__table__.c.ram,
    Asset.__table__.c.storage_spec,
    Asset.__table__.c.display,
    Asset.__table__.c.graphics,
    Asset.__table__.c.operating_system,
    Asset.__table__.c.battery,
    Asset.__table__.c.color,
    Asset.__table__.c.sold_to_name,
    Asset.__table__.c.sold_to_email,
    Asset.__table__.c.sold_date,
    Asset.__table__.c.sale_price,
    Asset.__table__.c.terms_and_conditions,
    Asset.__table__.c.sale_terms_email_sent_at,
    Asset.__table__.c.sale_terms_accepted_at,
    Asset.__table__.c.sale_terms_accepted_ip,
    Asset.__table__.c.sale_terms_acceptance_user_agent,
    Asset.__table__.c.delivery_receipt_sent_at,
    Asset.__table__.c.share_token,
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


def ensure_asset_schema():
    Asset.__table__.create(db.engine, checkfirst=True)
    db.session.commit()

    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if Asset.__tablename__ not in table_names:
        return

    asset_columns = {column["name"] for column in inspector.get_columns(Asset.__tablename__)}
    dialect = db.engine.dialect.name
    table_name = f'"{Asset.__tablename__}"' if dialect == "postgresql" else Asset.__tablename__

    added_columns = []
    for column in ASSET_EXTRA_COLUMNS:
        if column.name in asset_columns:
            continue

        column_sql = str(CreateColumn(column).compile(dialect=db.engine.dialect))
        if dialect == "postgresql":
            sql = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_sql}"
        else:
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"

        db.session.execute(text(sql))
        added_columns.append(column.name)

    if added_columns:
        db.session.commit()
        print(f"[schema] Added asset columns: {', '.join(added_columns)}")

    for index in Asset.__table__.indexes:
        index.create(db.engine, checkfirst=True)

    db.session.commit()
    print("[schema] Asset table ready")


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

    # Ensure refund_type column exists on existing invoice_refund table
    inspector = inspect(db.engine)
    if InvoiceRefund.__tablename__ in set(inspector.get_table_names()):
        refund_columns = {column["name"] for column in inspector.get_columns(InvoiceRefund.__tablename__)}
        if "refund_type" not in refund_columns:
            dialect = db.engine.dialect.name
            if dialect == "postgresql":
                sql = "ALTER TABLE invoice_refund ADD COLUMN IF NOT EXISTS refund_type VARCHAR(20) NOT NULL DEFAULT 'rupees'"
            else:
                sql = "ALTER TABLE invoice_refund ADD COLUMN refund_type VARCHAR(20) NOT NULL DEFAULT 'rupees'"
            db.session.execute(text(sql))
            db.session.commit()
            print("[schema] Added invoice_refund.refund_type")

    print("[schema] Invoice refund tables ready")


def main():
    wait_for_database(app)
    with app.app_context():
        ensure_user_columns()
        ensure_asset_schema()
        ensure_superscoins_tables()
        ensure_rollback_terms_tables()
        ensure_invoice_refund_schema()


if __name__ == "__main__":
    main()
