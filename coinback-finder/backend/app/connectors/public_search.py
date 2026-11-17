"""Permitted public search discovery through official search APIs only."""

from __future__ import annotations

from typing import Any

from app.classifier.patterns import COIN_RE
from app.connectors.base import (
    ConnectorError,
    DiscoveryContext,
    DiscoveryResult,
    ProductObservation,
    SourceConnector,
    build_queries,
)
from app.database.enums import SourceType
from app.discovery.url_validation import UrlValidationError, validate_flipkart_url


class _SearchConnector(SourceConnector):
    source_type = SourceType.PUBLIC_SEARCH
    auth_method = "api_key_env"
    default_rate_limit_per_minute = 10

    def _search(self, query: str, count: int) -> list[dict[str, Any]]:
        raise NotImplementedError

    def discover(self, ctx: DiscoveryContext) -> DiscoveryResult:
        result = DiscoveryResult()
        count = max(1, min(int(self.config.get("results_per_query", 10)), 20))
        seen: set[str] = set()
        for query in build_queries(self.config, ctx.run_sequence):
            if not ctx.rate_limiter.acquire(ctx.stop_event):
                break
            items = self._search(query, count)
            result.requests_made += 1
            for item in items:
                url, title, snippet, image = item.get("url"), item.get("title") or "", item.get("snippet") or "", item.get("image")
                if not url:
                    continue
                try:
                    validated = validate_flipkart_url(url, self.settings.flipkart_host_list)
                except UrlValidationError:
                    continue
                if not validated.is_product_page or validated.canonical_url in seen:
                    continue
                if not (COIN_RE.search(snippet) or COIN_RE.search(title)):
                    continue
                seen.add(validated.canonical_url)
                result.observations.append(
                    ProductObservation(
                        url=validated.canonical_url,
                        evidence_source=SourceType.PUBLIC_SEARCH,
                        title=_clean_title(title),
                        image_url=image,
                        offer_texts=[t for t in (snippet, title) if t],
                        evidence={"provider": self.key, "query": query, "result_title": title, "snippet": snippet},
                    )
                )
            ctx.log("info", f"{self.display_name}: query '{query}' returned {len(items)} results")
        return result


def _clean_title(title: str) -> str | None:
    cleaned = title.split(" | Flipkart")[0].split(" - Buy ")[0].strip()
    return cleaned or None


class GoogleCseConnector(_SearchConnector):
    key = "google_cse"
    display_name = "Google Programmable Search"
    permitted_use = "Official Custom Search JSON API; subject to Google API terms and quota."

    def is_configured(self) -> tuple[bool, str | None]:
        if not (self.settings.google_cse_api_key and self.settings.google_cse_engine_id):
            return False, "GOOGLE_CSE_API_KEY and GOOGLE_CSE_ENGINE_ID are not set."
        if not self.config.get("phrases"):
            return False, "No search phrases configured."
        return True, None

    def _search(self, query: str, count: int) -> list[dict[str, Any]]:
        data = self.http.get_json(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": self.settings.google_cse_api_key,
                "cx": self.settings.google_cse_engine_id,
                "q": f"{query} site:flipkart.com",
                "num": min(count, 10),
                "gl": "in",
            },
        )
        if not isinstance(data, dict):
            raise ConnectorError("Unexpected search response.")
        out = []
        for item in data.get("items", []) or []:
            pagemap = item.get("pagemap") or {}
            images = pagemap.get("cse_image") or []
            out.append({
                "url": item.get("link"),
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "image": images[0].get("src") if images and isinstance(images[0], dict) else None,
            })
        return out


class BraveSearchConnector(_SearchConnector):
    key = "brave_search"
    display_name = "Brave Search API"
    permitted_use = "Official Brave Web Search API; subject to Brave API terms and plan limits."

    def is_configured(self) -> tuple[bool, str | None]:
        if not self.settings.brave_search_api_key:
            return False, "BRAVE_SEARCH_API_KEY is not set."
        if not self.config.get("phrases"):
            return False, "No search phrases configured."
        return True, None

    def _search(self, query: str, count: int) -> list[dict[str, Any]]:
        data = self.http.get_json(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": f"{query} site:flipkart.com", "count": count, "country": "in"},
            headers={"Accept": "application/json", "X-Subscription-Token": self.settings.brave_search_api_key or ""},
        )
        if not isinstance(data, dict):
            raise ConnectorError("Unexpected search response.")
        results = (data.get("web") or {}).get("results") or []
        return [
            {
                "url": r.get("url"),
                "title": r.get("title"),
                "snippet": r.get("description"),
                "image": (r.get("thumbnail") or {}).get("src"),
            }
            for r in results
            if isinstance(r, dict)
        ]
