"""Idempotent creation of default sources, preferences and settings."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.enums import SourceType
from app.database.models import AppSetting, DiscoverySource, NotificationPreference
from app.services.settings_store import EDITABLE_DEFAULTS

DEFAULT_PHRASES = [
    "Flipkart 100% SuperCoin offer",
    "Flipkart 100% CoinBack",
    "Flipkart SuperCoins on purchase",
    "Flipkart cashback products",
    "Flipkart earn SuperCoins",
    "promotional SuperCoin offer",
    "get 500 SuperCoins",
    "up to 100% SuperCoins",
]
DEFAULT_CATEGORIES: list[str] = []

DEFAULT_SOURCES = [
    {
        "name": "User-submitted URLs",
        "source_type": SourceType.USER_SUBMITTED,
        "connector_key": "user_submitted",
        "enabled": True,
        "auth_method": "none",
        "rate_limit_per_minute": 30,
        "config": {},
        "permitted_use_notes": "Product URLs submitted by the operator. Validated against the Flipkart domain allowlist.",
    },
    {
        "name": "Google Programmable Search",
        "source_type": SourceType.PUBLIC_SEARCH,
        "connector_key": "google_cse",
        "enabled": False,
        "auth_method": "api_key_env",
        "rate_limit_per_minute": 10,
        "config": {"phrases": DEFAULT_PHRASES, "categories": DEFAULT_CATEGORIES, "max_queries_per_run": 4, "results_per_query": 10},
        "permitted_use_notes": "Official Custom Search JSON API. Requires GOOGLE_CSE_API_KEY and GOOGLE_CSE_ENGINE_ID. Snippets are discovery evidence only.",
    },
    {
        "name": "Brave Search API",
        "source_type": SourceType.PUBLIC_SEARCH,
        "connector_key": "brave_search",
        "enabled": False,
        "auth_method": "api_key_env",
        "rate_limit_per_minute": 10,
        "config": {"phrases": DEFAULT_PHRASES, "categories": DEFAULT_CATEGORIES, "max_queries_per_run": 4, "results_per_query": 20},
        "permitted_use_notes": "Official Brave Web Search API. Requires BRAVE_SEARCH_API_KEY. Snippets are discovery evidence only.",
    },
    {
        "name": "Flipkart product pages",
        "source_type": SourceType.PRODUCT_PAGE,
        "connector_key": "flipkart_product_page",
        "enabled": False,
        "auth_method": "none",
        "rate_limit_per_minute": 6,
        "config": {},
        "permitted_use_notes": (
            "Disabled by default. Requires PRODUCT_PAGE_FETCH_ENABLED=true and PRODUCT_PAGE_PERMISSION_CONFIRMED=true, "
            "which the operator may set only after confirming automated access is permitted. Honours robots.txt; "
            "never bypasses CAPTCHA, login or anti-bot controls."
        ),
    },
    {
        "name": "Authorized JSON feed",
        "source_type": SourceType.THIRD_PARTY,
        "connector_key": "json_feed",
        "enabled": False,
        "auth_method": "api_key_env",
        "rate_limit_per_minute": 10,
        "config": {"url": "", "api_key_env": "THIRD_PARTY_FEED_API_KEY", "auth_header": "Authorization", "auth_scheme": "Bearer"},
        "permitted_use_notes": "Provider-independent feed connector for an authorized data provider. Host must be listed in THIRD_PARTY_ALLOWED_HOSTS.",
    },
]


def ensure_defaults(db: Session) -> None:
    existing = set(db.scalars(select(DiscoverySource.connector_key)).all())
    for spec in DEFAULT_SOURCES:
        if spec["connector_key"] not in existing:
            db.add(DiscoverySource(**spec))

    db.execute(insert(NotificationPreference).values(scope="global").on_conflict_do_nothing(index_elements=["scope"]))
    for key, value in EDITABLE_DEFAULTS.items():
        db.execute(insert(AppSetting).values(key=key, value=value).on_conflict_do_nothing(index_elements=["key"]))
    db.commit()
