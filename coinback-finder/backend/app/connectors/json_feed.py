"""Authorized third-party JSON feed connector.

Expected payload: {"items": [{"url", "title", "brand", "category", "image_url", "seller",
"selling_price", "mrp", "shipping_charge", "in_stock", "offers": ["offer text", ...]}]}
"""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlsplit

from app.connectors.base import ConnectorError, DiscoveryContext, DiscoveryResult, ProductObservation, SourceConnector
from app.connectors.product_page import _to_decimal
from app.database.enums import SourceType

_ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
# Application secrets must never be forwarded to an external provider.
_FORBIDDEN_ENV = {
    "SECRET_KEY", "DATABASE_URL", "POSTGRES_PASSWORD", "TELEGRAM_BOT_TOKEN",
    "GOOGLE_CSE_API_KEY", "BRAVE_SEARCH_API_KEY", "ADMIN_PASSWORD",
}
MAX_ITEMS = 500


def _str(value: Any, limit: int = 500) -> str | None:
    return value.strip()[:limit] if isinstance(value, str) and value.strip() else None


class JsonFeedConnector(SourceConnector):
    key = "json_feed"
    display_name = "Authorized JSON feed"
    source_type = SourceType.THIRD_PARTY
    auth_method = "api_key_env"
    permitted_use = "Only for providers that have authorized this use. Feed host must be allowlisted."

    def _feed_url(self) -> str | None:
        url = _str(self.config.get("url"), 2048)
        if not url:
            return None
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if parts.scheme != "https" or parts.username or host not in self.settings.third_party_host_list:
            return None
        return url

    def _api_key(self) -> tuple[str | None, str | None]:
        env_name = self.config.get("api_key_env")
        if not env_name:
            return None, None
        if not isinstance(env_name, str) or not _ENV_NAME_RE.match(env_name) or env_name in _FORBIDDEN_ENV:
            return None, "api_key_env must name a dedicated provider variable."
        value = os.environ.get(env_name)
        return (value, None) if value else (None, f"Environment variable {env_name} is not set.")

    def is_configured(self) -> tuple[bool, str | None]:
        if not self._feed_url():
            return False, "Feed URL missing, not HTTPS, or host not in THIRD_PARTY_ALLOWED_HOSTS."
        _, err = self._api_key()
        if err:
            return False, err
        return True, None

    def discover(self, ctx: DiscoveryContext) -> DiscoveryResult:
        url = self._feed_url()
        if not url:
            raise ConnectorError("Feed not configured.")
        headers = {"Accept": "application/json"}
        key, _ = self._api_key()
        if key:
            scheme = _str(self.config.get("auth_scheme"), 32)
            header = _str(self.config.get("auth_header"), 64) or "Authorization"
            headers[header] = f"{scheme} {key}" if scheme else key
        if not ctx.rate_limiter.acquire(ctx.stop_event):
            return DiscoveryResult()
        data = self.http.get_json(url, headers=headers)
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise ConnectorError("Feed payload missing 'items' list.")

        result = DiscoveryResult(requests_made=1)
        for raw in items[:MAX_ITEMS]:
            if not isinstance(raw, dict) or not _str(raw.get("url"), 2048):
                continue
            offers = [o[:1000] for o in raw.get("offers") or [] if isinstance(o, str)]
            in_stock = raw.get("in_stock")
            result.observations.append(
                ProductObservation(
                    url=raw["url"].strip(),
                    evidence_source=SourceType.THIRD_PARTY,
                    title=_str(raw.get("title")),
                    brand=_str(raw.get("brand"), 255),
                    category=_str(raw.get("category"), 255),
                    image_url=_str(raw.get("image_url"), 2048),
                    seller=_str(raw.get("seller"), 255),
                    selling_price=_to_decimal(raw.get("selling_price")),
                    mrp=_to_decimal(raw.get("mrp")),
                    shipping_charge=_to_decimal(raw.get("shipping_charge")),
                    in_stock=in_stock if isinstance(in_stock, bool) else None,
                    offer_texts=offers,
                    evidence={"provider": self.config.get("provider_name") or "json_feed"},
                )
            )
        ctx.log("info", f"{self.display_name}: received {len(result.observations)} items")
        return result
