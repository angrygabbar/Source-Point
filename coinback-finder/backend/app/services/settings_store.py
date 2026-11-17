"""Typed access to operator-editable settings stored in app_settings."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.models import AppSetting

EDITABLE_DEFAULTS: dict[str, Any] = {
    "scan_interval_minutes": 15,
    # INR value per SuperCoin used only for labelled estimates. NULL = no conversion assumed.
    "supercoin_value_inr": None,
    "retention_days_scan_runs": 90,
    "retention_days_notifications": 180,
    "price_snapshot_min_interval_minutes": 60,
    "default_theme": "light",
    "monitor_new_submissions": True,
}

RUNTIME_KEYS = {"scanner_heartbeat", "telegram_update_offset", "scan_sequence"}


@dataclass(frozen=True)
class AppConfig:
    scan_interval_minutes: int
    supercoin_value_inr: float | None
    retention_days_scan_runs: int
    retention_days_notifications: int
    price_snapshot_min_interval_minutes: int
    default_theme: str
    monitor_new_submissions: bool

    @property
    def coin_value(self) -> Decimal | None:
        return None if self.supercoin_value_inr is None else Decimal(str(self.supercoin_value_inr))

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_value(db: Session, key: str, default: Any = None) -> Any:
    row = db.get(AppSetting, key)
    return default if row is None else row.value


def set_value(db: Session, key: str, value: Any) -> None:
    stmt = insert(AppSetting).values(key=key, value=value)
    stmt = stmt.on_conflict_do_update(index_elements=[AppSetting.key], set_={"value": value})
    db.execute(stmt)


def get_app_config(db: Session) -> AppConfig:
    rows = db.scalars(select(AppSetting).where(AppSetting.key.in_(EDITABLE_DEFAULTS.keys()))).all()
    values = dict(EDITABLE_DEFAULTS)
    values.update({r.key: r.value for r in rows})
    return AppConfig(**values)


def update_app_config(db: Session, changes: dict[str, Any]) -> AppConfig:
    for key, value in changes.items():
        if key in EDITABLE_DEFAULTS:
            set_value(db, key, value)
    db.flush()
    return get_app_config(db)
