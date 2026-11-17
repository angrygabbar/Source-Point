"""HTTP client with allowlist enforcement, manual redirect validation, robots.txt and timeouts."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.config import Settings
from app.connectors.base import AccessBlocked, AccessNotPermitted, ConnectorError, RateLimited
from app.discovery.url_validation import is_allowed_host

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 5 * 1024 * 1024
ROBOTS_TTL_SECONDS = 6 * 3600
MAX_REDIRECTS = 3


def _looks_like_challenge(text: str) -> bool:
    head = text[:20000].lower()
    if "are you a human" in head or "verify you are human" in head:
        return True
    return "captcha" in head and "application/ld+json" not in head


class SafeHttpClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = httpx.Client(
            timeout=httpx.Timeout(settings.http_timeout_seconds),
            follow_redirects=False,
            headers={"User-Agent": settings.http_user_agent, "Accept-Language": "en-IN,en;q=0.8"},
        )
        self._robots: dict[str, tuple[float, RobotFileParser | None, bool]] = {}
        self._lock = threading.Lock()

    def close(self) -> None:
        self._client.close()

    def get_json(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        """For fixed, operator-configured API endpoints."""
        try:
            resp = self._client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise ConnectorError("Request timed out.") from exc
        except httpx.HTTPError as exc:
            raise ConnectorError(f"Network error: {type(exc).__name__}") from exc
        if resp.status_code == 429:
            retry_after = resp.headers.get("retry-after")
            raise RateLimited("Provider rate limit reached (HTTP 429).", int(retry_after) if retry_after and retry_after.isdigit() else None)
        if resp.status_code in (401, 403):
            raise ConnectorError(f"Provider rejected credentials or access (HTTP {resp.status_code}).")
        if resp.status_code >= 400:
            raise ConnectorError(f"Provider returned HTTP {resp.status_code}.")
        if len(resp.content) > MAX_BODY_BYTES:
            raise ConnectorError("Provider response too large.")
        try:
            return resp.json()
        except ValueError as exc:
            raise ConnectorError("Provider returned invalid JSON.") from exc

    def get_allowlisted_page(self, url: str, allowed_hosts: list[str]) -> httpx.Response:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            if not is_allowed_host(current, allowed_hosts):
                raise AccessNotPermitted("Blocked request to a host outside the approved allowlist.")
            if not self.robots_allowed(current, allowed_hosts):
                raise AccessNotPermitted("Disallowed by robots.txt for this user agent.")
            try:
                resp = self._client.get(current, headers={"Accept": "text/html,application/xhtml+xml"})
            except httpx.TimeoutException as exc:
                raise ConnectorError("Page request timed out.") from exc
            except httpx.HTTPError as exc:
                raise ConnectorError(f"Network error: {type(exc).__name__}") from exc

            if resp.is_redirect:
                location = resp.headers.get("location")
                if not location:
                    raise ConnectorError("Redirect without location.")
                current = urljoin(current, location)
                continue
            if resp.status_code in (403, 429, 503):
                raise AccessBlocked(f"Access refused by source (HTTP {resp.status_code}). Not retried by circumvention.")
            if resp.status_code == 404:
                raise ConnectorError("Product page not found (HTTP 404).")
            if resp.status_code >= 400:
                raise ConnectorError(f"Page returned HTTP {resp.status_code}.")
            if len(resp.content) > MAX_BODY_BYTES:
                raise ConnectorError("Page too large.")
            if _looks_like_challenge(resp.text):
                raise AccessBlocked("Source presented a challenge page (CAPTCHA/bot check). Access stopped.")
            return resp
        raise ConnectorError("Too many redirects.")

    def robots_allowed(self, url: str, allowed_hosts: list[str]) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        now = time.monotonic()
        with self._lock:
            cached = self._robots.get(origin)
        if cached is None or now - cached[0] > ROBOTS_TTL_SECONDS:
            cached = (now, *self._load_robots(origin, allowed_hosts))
            with self._lock:
                self._robots[origin] = cached
        _, parser, allow_all = cached
        if parser is None:
            return allow_all
        return parser.can_fetch(self.settings.http_user_agent, url)

    def _load_robots(self, origin: str, allowed_hosts: list[str]) -> tuple[RobotFileParser | None, bool]:
        robots_url = f"{origin}/robots.txt"
        if not is_allowed_host(robots_url, allowed_hosts):
            return None, False
        try:
            resp = self._client.get(robots_url)
        except httpx.HTTPError:
            logger.warning("robots.txt unreachable for %s; treating as disallowed", origin)
            return None, False
        if resp.status_code in (401, 403):
            return None, False
        if 400 <= resp.status_code < 500:
            return None, True
        if resp.status_code >= 300:
            return None, False
        parser = RobotFileParser()
        parser.parse(resp.text.splitlines())
        return parser, False
