"""Flipkart URL validation and normalisation (allowlist + SSRF protection)."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

MAX_URL_LENGTH = 2048
CANONICAL_HOST = "www.flipkart.com"
_ITEM_RE = re.compile(r"/p/(itm[0-9a-z]{6,})", re.IGNORECASE)
_PID_RE = re.compile(r"^[A-Z0-9]{8,32}$")


class UrlValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedUrl:
    original_url: str
    canonical_url: str
    host: str
    pid: str | None
    item_id: str | None

    @property
    def is_product_page(self) -> bool:
        return self.item_id is not None

    @property
    def normalized_url(self) -> str:
        return self.canonical_url


def _reject_ip_literal(host: str) -> None:
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return
    raise UrlValidationError("IP addresses are not permitted; use a Flipkart product URL.")


def validate_flipkart_url(raw: str, allowed_hosts: list[str]) -> ValidatedUrl:
    if not isinstance(raw, str):
        raise UrlValidationError("URL must be text.")
    value = raw.strip()
    if not value:
        raise UrlValidationError("URL is empty.")
    if len(value) > MAX_URL_LENGTH:
        raise UrlValidationError("URL is too long.")
    if any(ch.isspace() for ch in value):
        raise UrlValidationError("URL must not contain whitespace.")
    if "://" not in value:
        value = "https://" + value

    parts = urlsplit(value)
    if parts.scheme.lower() not in {"http", "https"}:
        raise UrlValidationError("Only http and https URLs are accepted.")
    if parts.username or parts.password:
        raise UrlValidationError("URLs containing credentials are not accepted.")
    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise UrlValidationError("URL has no host.")
    _reject_ip_literal(host)
    try:
        port = parts.port
    except ValueError as exc:
        raise UrlValidationError("URL port is invalid.") from exc
    if port not in (None, 80, 443):
        raise UrlValidationError("Non-standard ports are not accepted.")
    if host not in allowed_hosts:
        raise UrlValidationError(f"Host '{host}' is not an approved Flipkart domain.")

    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if host == "dl.flipkart.com":
        if path.startswith("/dl/"):
            path = path[3:]
        elif path.startswith("/s/"):
            raise UrlValidationError(
                "Short links cannot be resolved without contacting Flipkart. Open the link in your browser and paste the full product URL."
            )

    query = parse_qs(parts.query)
    pid_raw = (query.get("pid") or [None])[0]
    pid = pid_raw.upper() if pid_raw and _PID_RE.match(pid_raw.upper()) else None

    item_match = _ITEM_RE.search(path)
    item_id = item_match.group(1).lower() if item_match else None
    if item_match:
        path = path[: item_match.end()]
    path = path.rstrip("/").lower() or "/"

    canonical = urlunsplit(("https", CANONICAL_HOST, path, urlencode({"pid": pid}) if pid else "", ""))
    return ValidatedUrl(original_url=raw.strip(), canonical_url=canonical, host=host, pid=pid, item_id=item_id)


def is_allowed_host(url: str, allowed_hosts: list[str]) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    host = (parts.hostname or "").lower().rstrip(".")
    return parts.scheme in {"http", "https"} and host in allowed_hosts and not parts.username
