"""Request validation models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

def _money() -> Any:
    return Field(default=None, ge=0, le=Decimal("100000000"), max_digits=12, decimal_places=2)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginIn(Strict):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(Strict):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=72)


class ProductSubmitIn(Strict):
    url: str = Field(min_length=10, max_length=2048)
    monitor: bool = True


class ProductUpdateIn(Strict):
    title: str | None = Field(default=None, max_length=1000)
    brand: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=255)
    seller: str | None = Field(default=None, max_length=255)
    variant: str | None = Field(default=None, max_length=255)
    image_url: str | None = Field(default=None, max_length=2048)
    current_price: Decimal | None = _money()
    mrp: Decimal | None = _money()
    shipping_charge: Decimal | None = _money()
    in_stock: bool | None = None

    @field_validator("image_url")
    @classmethod
    def _https_only(cls, v: str | None) -> str | None:
        if v and not v.startswith("https://"):
            raise ValueError("Image URL must use https.")
        return v


class ManualOfferIn(Strict):
    text: str = Field(min_length=6, max_length=2000)


class VerifyIn(Strict):
    status: Literal["VERIFIED", "ACCOUNT_CHECK_REQUIRED"] = "VERIFIED"
    actual_reward_coins: int | None = Field(default=None, ge=0, le=10_000_000)
    eligible_purchase_amount: Decimal | None = _money()
    reward_cap_coins: int | None = Field(default=None, ge=0, le=10_000_000)
    actual_redemption_value: Decimal | None = _money()
    restrictions: str | None = Field(default=None, max_length=1000)
    expiry: datetime | None = None
    eligibility_notes: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    observed_at: datetime | None = None


class RejectIn(Strict):
    notes: str | None = Field(default=None, max_length=2000)


class MonitorIn(Strict):
    frequency_minutes: int | None = Field(default=None, ge=5, le=1440)


class DiscoveryRunIn(Strict):
    source_id: UUID | None = None


class SourceUpdateIn(Strict):
    enabled: bool | None = None
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=120)
    phrases: list[str] | None = Field(default=None, max_length=50)
    categories: list[str] | None = Field(default=None, max_length=50)
    max_queries_per_run: int | None = Field(default=None, ge=1, le=20)
    results_per_query: int | None = Field(default=None, ge=1, le=20)
    feed_url: str | None = Field(default=None, max_length=2048)
    api_key_env: str | None = Field(default=None, max_length=64, pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    provider_name: str | None = Field(default=None, max_length=120)

    @field_validator("phrases", "categories")
    @classmethod
    def _clean_list(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        cleaned = [" ".join(s.split())[:120] for s in v if isinstance(s, str) and s.strip()]
        return list(dict.fromkeys(cleaned))


class PreferencesIn(Strict):
    enabled: bool
    paused: bool
    min_percentage: Literal[10, 25, 50, 75, 100] | None = None
    verified_only: bool
    include_unverified: bool
    notify_new: bool
    notify_changes: bool
    notify_expiring: bool


class SettingsIn(Strict):
    scan_interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    supercoin_value_inr: float | None = Field(default=None, ge=0, le=10)
    clear_supercoin_value: bool = False
    retention_days_scan_runs: int | None = Field(default=None, ge=7, le=3650)
    retention_days_notifications: int | None = Field(default=None, ge=7, le=3650)
    price_snapshot_min_interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    default_theme: Literal["light", "dark"] | None = None
    monitor_new_submissions: bool | None = None


class WatchlistIn(Strict):
    product_id: UUID
    note: str | None = Field(default=None, max_length=1000)
    target_price: Decimal | None = _money()
    target_percentage: Decimal | None = Field(default=None, ge=0, le=1000)


class SavedFilterIn(Strict):
    page: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9\-_/]+$")
    name: str = Field(min_length=1, max_length=120)
    params: dict[str, Any]

    @field_validator("params")
    @classmethod
    def _small(cls, v: dict[str, Any]) -> dict[str, Any]:
        if len(v) > 40 or any(not isinstance(k, str) or len(k) > 64 for k in v):
            raise ValueError("Too many or invalid filter keys.")
        return {k: val for k, val in v.items() if isinstance(val, (str, int, float, bool)) and len(str(val)) <= 500}
