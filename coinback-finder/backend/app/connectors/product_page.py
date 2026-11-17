"""Flipkart product-page connector. Disabled unless the operator confirms access is permitted."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup

from app.classifier.patterns import COIN_RE
from app.connectors.base import (
    AccessNotPermitted,
    DiscoveryContext,
    ProductObservation,
    SourceConnector,
)
from app.database.enums import SourceType

MAX_OFFER_TEXTS = 25


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        number = Decimal(str(value).replace(",", "").replace("₹", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number >= 0 else None


def _iter_nodes(data: Any):
    if isinstance(data, list):
        for item in data:
            yield from _iter_nodes(item)
    elif isinstance(data, dict):
        yield data
        graph = data.get("@graph")
        if graph:
            yield from _iter_nodes(graph)


def _type_is(node: dict[str, Any], name: str) -> bool:
    t = node.get("@type")
    return t == name or (isinstance(t, list) and name in t)


def parse_product_page(html: str, url: str) -> ProductObservation:
    soup = BeautifulSoup(html, "html.parser")
    product_ld: dict[str, Any] | None = None
    breadcrumb_ld: dict[str, Any] | None = None
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except (ValueError, TypeError):
            continue
        for node in _iter_nodes(data):
            if product_ld is None and _type_is(node, "Product"):
                product_ld = node
            if breadcrumb_ld is None and _type_is(node, "BreadcrumbList"):
                breadcrumb_ld = node

    obs = ProductObservation(url=url, evidence_source=SourceType.PRODUCT_PAGE, complete_page=True)

    if product_ld:
        obs.title = product_ld.get("name")
        brand = product_ld.get("brand")
        obs.brand = brand.get("name") if isinstance(brand, dict) else brand if isinstance(brand, str) else None
        image = product_ld.get("image")
        obs.image_url = image[0] if isinstance(image, list) and image else image if isinstance(image, str) else None
        offers = product_ld.get("offers")
        offer = offers[0] if isinstance(offers, list) and offers else offers if isinstance(offers, dict) else None
        if offer:
            obs.selling_price = _to_decimal(offer.get("price") or offer.get("lowPrice"))
            availability = str(offer.get("availability") or "")
            if availability:
                obs.in_stock = "InStock" in availability
            seller = offer.get("seller")
            if isinstance(seller, dict) and isinstance(seller.get("name"), str):
                obs.seller = seller["name"][:255]

    if breadcrumb_ld:
        items = breadcrumb_ld.get("itemListElement") or []
        names = [i.get("name") or (i.get("item") or {}).get("name") for i in items if isinstance(i, dict)]
        names = [n for n in names if isinstance(n, str) and n.lower() != "home"]
        if len(names) >= 2:
            obs.category = names[-2][:255]
        elif names:
            obs.category = names[0][:255]

    if not obs.title:
        og = soup.find("meta", attrs={"property": "og:title"})
        obs.title = og.get("content") if og else (soup.h1.get_text(" ", strip=True) if soup.h1 else None)
    if not obs.image_url:
        og_img = soup.find("meta", attrs={"property": "og:image"})
        obs.image_url = og_img.get("content") if og_img else None

    texts: list[str] = []
    seen: set[str] = set()
    for node in soup.find_all(string=COIN_RE):
        element = node.parent
        for _ in range(2):
            if element is None or element.parent is None:
                break
            if len(element.get_text(" ", strip=True)) >= 160:
                break
            element = element.parent
        text = " ".join((element.get_text(" ", strip=True) if element else str(node)).split())[:600]
        if text and text not in seen:
            seen.add(text)
            texts.append(text)
        if len(texts) >= MAX_OFFER_TEXTS:
            break
    obs.offer_texts = texts
    obs.evidence = {"parser": "json-ld+text", "json_ld_product": product_ld is not None, "offer_text_blocks": len(texts)}
    return obs


class FlipkartProductPageConnector(SourceConnector):
    key = "flipkart_product_page"
    display_name = "Flipkart product pages"
    source_type = SourceType.PRODUCT_PAGE
    permitted_use = "Only when the operator has confirmed permission. Honours robots.txt; stops on challenges."
    default_rate_limit_per_minute = 6
    supports_discovery = False
    supports_product_fetch = True

    def is_configured(self) -> tuple[bool, str | None]:
        if not self.settings.product_page_fetch_enabled:
            return False, "Product page access disabled (PRODUCT_PAGE_FETCH_ENABLED=false)."
        if not self.settings.product_page_permission_confirmed:
            return False, "Permission for automated page access not confirmed (PRODUCT_PAGE_PERMISSION_CONFIRMED=false)."
        return True, None

    def fetch_product(self, url: str, ctx: DiscoveryContext) -> ProductObservation:
        ready, reason = self.is_configured()
        if not ready:
            raise AccessNotPermitted(reason or "Not permitted.")
        if not ctx.rate_limiter.acquire(ctx.stop_event):
            raise AccessNotPermitted("Scanner shutting down.")
        resp = self.http.get_allowlisted_page(url, self.settings.flipkart_host_list)
        return parse_product_page(resp.text, url)
