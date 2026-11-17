"""Integration tests require a disposable PostgreSQL database and are skipped by default.

Set COINBACK_TEST_DATABASE_URL to a throwaway database to enable them. Never point this at production data.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("COINBACK_TEST_DATABASE_URL"), reason="COINBACK_TEST_DATABASE_URL not set")


def test_ingestion_creates_product_offer_and_snapshot():
    os.environ["DATABASE_URL"] = os.environ["COINBACK_TEST_DATABASE_URL"]
    from sqlalchemy import select

    from app.connectors.base import ProductObservation
    from app.database.enums import SourceType
    from app.database.models import Base, Offer, OfferSnapshot, PriceHistory
    from app.database.session import SessionLocal, engine
    from app.services.ingestion import ingest_observation
    from app.services.settings_store import get_app_config

    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        obs = ProductObservation(
            url="https://www.flipkart.com/test-item/p/itmtest00001?pid=TESTPID00001",
            evidence_source=SourceType.THIRD_PARTY,
            title="Test item",
            selling_price=2000,
            offer_texts=["Get 100% SuperCoins back, up to 500 SuperCoins"],
        )
        outcome = ingest_observation(db, obs, source=None, config=get_app_config(db))
        db.commit()
        assert outcome.product_created
        assert len(outcome.new_offer_ids) == 1
        offer = db.get(Offer, outcome.new_offer_ids[0])
        assert offer.estimated_coins == 500
        assert db.scalar(select(OfferSnapshot).where(OfferSnapshot.offer_id == offer.id)) is not None
        assert db.scalar(select(PriceHistory).where(PriceHistory.product_id == offer.product_id)) is not None
