"""Provider-independent connector interface."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from app.config import Settings
    from app.connectors.http import SafeHttpClient
    from app.scanner.rate_limit import RateLimiter


class ConnectorError(Exception):
    """Recoverable source failure; triggers backoff for the source."""


class RateLimited(ConnectorError):
    def __init__(self, message: str, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class AccessBlocked(ConnectorError):
    """The source refused access (HTTP 403/429/challenge). Never retried by circumvention."""


class AccessNotPermitted(ConnectorError):
    """Access is not permitted by configuration or robots.txt."""


@dataclass
class ProductObservation:
    url: str
    evidence_source: str
    title: str | None = None
    brand: str | None = None
    category: str | None = None
    image_url: str | None = None
    seller: str | None = None
    selling_price: Decimal | None = None
    mrp: Decimal | None = None
    shipping_charge: Decimal | None = None
    in_stock: bool | None = None
    variant: str | None = None
    offer_texts: list[str] = field(default_factory=list)
    # True only when the observation reflects the complete current product page.
    complete_page: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryResult:
    observations: list[ProductObservation] = field(default_factory=list)
    requests_made: int = 0
    notes: list[str] = field(default_factory=list)


@dataclass
class DiscoveryContext:
    rate_limiter: RateLimiter
    stop_event: threading.Event
    run_sequence: int
    log: Callable[[str, str], None]


@dataclass(frozen=True)
class ConnectorInfo:
    key: str
    display_name: str
    source_type: str
    auth_method: str
    permitted_use: str
    default_rate_limit_per_minute: int
    supports_discovery: bool
    supports_product_fetch: bool


class SourceConnector(ABC):
    key: ClassVar[str]
    display_name: ClassVar[str]
    source_type: ClassVar[str]
    auth_method: ClassVar[str] = "none"
    permitted_use: ClassVar[str] = ""
    default_rate_limit_per_minute: ClassVar[int] = 10
    supports_discovery: ClassVar[bool] = True
    supports_product_fetch: ClassVar[bool] = False

    def __init__(self, config: dict[str, Any], settings: Settings, http: SafeHttpClient) -> None:
        self.config = config or {}
        self.settings = settings
        self.http = http

    @classmethod
    def info(cls) -> ConnectorInfo:
        return ConnectorInfo(
            key=cls.key,
            display_name=cls.display_name,
            source_type=cls.source_type,
            auth_method=cls.auth_method,
            permitted_use=cls.permitted_use,
            default_rate_limit_per_minute=cls.default_rate_limit_per_minute,
            supports_discovery=cls.supports_discovery,
            supports_product_fetch=cls.supports_product_fetch,
        )

    @abstractmethod
    def is_configured(self) -> tuple[bool, str | None]:
        """Return (ready, reason_if_not_ready)."""

    def discover(self, ctx: DiscoveryContext) -> DiscoveryResult:
        return DiscoveryResult()

    def fetch_product(self, url: str, ctx: DiscoveryContext) -> ProductObservation:
        raise AccessNotPermitted(f"{self.display_name} does not support product retrieval.")


def build_queries(config: dict[str, Any], run_sequence: int) -> list[str]:
    """Rotate through phrase × category combinations so each run stays within quota."""
    phrases = [p for p in config.get("phrases", []) if isinstance(p, str) and p.strip()]
    categories = [c for c in config.get("categories", []) if isinstance(c, str) and c.strip()]
    combos = [f"{p} {c}".strip() for p in phrases for c in (categories or [""])]
    if not combos:
        return []
    limit = max(1, min(int(config.get("max_queries_per_run", 4)), 20))
    start = (run_sequence * limit) % len(combos)
    rotated = combos[start:] + combos[:start]
    return rotated[:limit]
