import re
from datetime import datetime
from typing import Any, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException
from pydantic import BaseModel, Field

# Get Maine Lobster — Shopify + Okendo. Override via env in production if needed.
STORE_BASE = "https://getmainelobster.com"
OKENDO_SUBSCRIBER_ID = "b7b27e6e-688a-4da3-ad34-dbef41d9e64b"
OKENDO_API_BASE = "https://api.okendo.io/v1"
OKENDO_API_VERSION = "2025-02-01"
SHIPPING_POLICY_URL = f"{STORE_BASE}/policies/shipping-policy"
REQUEST_TIMEOUT = 30.0

_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ccp-scraper/1.0; +https://getmainelobster.com)",
    "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
}


def _okendo_headers() -> dict[str, str]:
    h = dict(_DEFAULT_HEADERS)
    h["okendo-api-version"] = OKENDO_API_VERSION
    return h


def _abs_store_url(value: str) -> str:
    if not value:
        return value
    if value.startswith("//"):
        return f"https:{value}"
    if value.startswith("/"):
        return f"{STORE_BASE}{value}"
    return value


def _shopify_cents_to_display(cents: int) -> str:
    return f"${cents / 100:.2f}"


def _html_to_text(html: str) -> str:
    if not html or not html.strip():
        return ""
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


class ProductVariantOut(BaseModel):
    id: int
    title: str
    price: str
    sku: Optional[str] = None
    available: bool = True
    weight: Optional[int] = None
    requires_shipping: bool = True
    options: List[str] = Field(default_factory=list)


class ReviewItem(BaseModel):
    review_id: str
    title: Optional[str] = None
    body: str
    rating: Optional[int] = None
    date_created: Optional[str] = None
    reviewer_name: Optional[str] = None
    is_verified: Optional[bool] = None
    is_recommended: Optional[bool] = None


class ProductFull(BaseModel):
    """Product detail: Shopify JSON + Okendo reviews + store shipping policy copy."""

    handle: str
    shopify_product_id: int
    title: str
    url: str
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    description_html: str
    description_text: str
    images: List[str] = Field(default_factory=list)
    variants: List[ProductVariantOut] = Field(default_factory=list)
    reviews: List[ReviewItem] = Field(default_factory=list)
    are_reviews_grouped: bool = False
    shipping_policy_text: Optional[str] = None
    shipping_policy_url: str = SHIPPING_POLICY_URL


def _fetch_json(url: str) -> Any:
    r = requests.get(url, headers=_DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Resource not found")
    r.raise_for_status()
    return r.json()


def _fetch_text(url: str) -> str:
    r = requests.get(url, headers=_DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def fetch_shopify_product_by_handle(handle: str) -> dict[str, Any]:
    slug = handle.strip().strip("/")
    if not slug or ".." in slug or "/" in slug:
        raise HTTPException(status_code=400, detail="Invalid product handle")
    url = f"{STORE_BASE}/products/{slug}.js"
    return _fetch_json(url)


def _variants_from_shopify(data: dict[str, Any]) -> List[ProductVariantOut]:
    out: List[ProductVariantOut] = []
    for v in data.get("variants") or []:
        price_raw = v.get("price")
        if isinstance(price_raw, (int, float)):
            price_str = _shopify_cents_to_display(int(price_raw))
        else:
            price_str = str(price_raw or "")
        opts = v.get("options")
        if not isinstance(opts, list):
            opts = []
        out.append(
            ProductVariantOut(
                id=int(v["id"]),
                title=str(v.get("title") or ""),
                price=price_str,
                sku=v.get("sku"),
                available=bool(v.get("available", True)),
                weight=v.get("weight"),
                requires_shipping=bool(v.get("requires_shipping", True)),
                options=[str(x) for x in opts],
            )
        )
    return out


def _images_from_shopify(data: dict[str, Any]) -> List[str]:
    urls: List[str] = []
    for img in data.get("images") or []:
        if isinstance(img, str):
            urls.append(_abs_store_url(img))
    return urls


# Only ever return this many review rows, newest first (Okendo Storefront API).
LATEST_REVIEW_COUNT = 10


def _review_sort_key(r: dict[str, Any]) -> float:
    raw = r.get("dateCreated") or ""
    if not raw:
        return 0.0
    s = str(raw).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return 0.0


def fetch_okendo_latest_reviews(
    shopify_product_id: int,
    *,
    count: int = LATEST_REVIEW_COUNT,
) -> Tuple[List[dict[str, Any]], bool]:
    """Fetch up to `count` most recent published reviews in one API call (date desc, Okendo 1–25)."""
    if count <= 0:
        return [], False
    n = min(25, count)
    base = f"{OKENDO_API_BASE}/stores/{OKENDO_SUBSCRIBER_ID}/products/shopify-{shopify_product_id}/reviews"
    r = requests.get(
        base,
        headers=_okendo_headers(),
        timeout=REQUEST_TIMEOUT,
        params={"limit": n, "orderBy": "date desc"},
    )
    r.raise_for_status()
    data = r.json()
    grouped = bool(data.get("areReviewsGrouped", False))
    reviews = [x for x in (data.get("reviews") or []) if isinstance(x, dict)]
    # Ensure newest-first in case the API order differs; then cap at `count`.
    reviews.sort(key=_review_sort_key, reverse=True)
    return reviews[:count], grouped


def _map_okendo_review(raw: dict[str, Any]) -> ReviewItem:
    reviewer = raw.get("reviewer") or {}
    name = None
    if isinstance(reviewer, dict):
        name = reviewer.get("displayName")
    return ReviewItem(
        review_id=str(raw.get("reviewId", "")),
        title=raw.get("title"),
        body=str(raw.get("body", "")),
        rating=raw.get("rating"),
        date_created=raw.get("dateCreated"),
        reviewer_name=name,
        is_verified=reviewer.get("isVerified") if isinstance(reviewer, dict) else None,
        is_recommended=raw.get("isRecommended"),
    )


_shipping_policy_cache: Optional[str] = None
_shipping_policy_fetched: bool = False


def fetch_shipping_policy_text() -> Optional[str]:
    global _shipping_policy_cache, _shipping_policy_fetched
    if _shipping_policy_fetched:
        return _shipping_policy_cache
    _shipping_policy_fetched = True
    try:
        html = _fetch_text(SHIPPING_POLICY_URL)
    except requests.RequestException:
        _shipping_policy_cache = None
        return None
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".shopify-policy__body") or soup.select_one("main")
    if not body:
        _shipping_policy_cache = None
        return None
    text = body.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    _shipping_policy_cache = text.strip() or None
    return _shipping_policy_cache


def build_product_full(handle: str, data: dict[str, Any], reviews: List[dict[str, Any]], grouped: bool) -> ProductFull:
    product_id = int(data["id"])
    desc = data.get("description") or data.get("content") or ""
    rel_url = str(data.get("url") or f"/products/{data.get('handle', handle)}")
    product_url = _abs_store_url(rel_url) if rel_url.startswith("/") else _abs_store_url(f"/{rel_url.lstrip('/')}")

    review_models = [_map_okendo_review(r) for r in reviews]
    tag_list = data.get("tags")
    if isinstance(tag_list, str):
        tag_list = [t.strip() for t in tag_list.split(",") if t.strip()]
    elif not isinstance(tag_list, list):
        tag_list = []

    return ProductFull(
        handle=str(data.get("handle") or handle),
        shopify_product_id=product_id,
        title=str(data.get("title") or ""),
        url=product_url,
        vendor=data.get("vendor"),
        product_type=data.get("type"),
        tags=[str(t) for t in tag_list],
        description_html=desc,
        description_text=_html_to_text(desc),
        images=_images_from_shopify(data),
        variants=_variants_from_shopify(data),
        reviews=review_models,
        are_reviews_grouped=grouped,
        shipping_policy_text=fetch_shipping_policy_text(),
        shipping_policy_url=SHIPPING_POLICY_URL,
    )


def fetch_product_full(handle: str) -> ProductFull:
    """Load Shopify product JSON, 10 latest Okendo reviews, and shipping policy text."""
    data = fetch_shopify_product_by_handle(handle)
    product_id = int(data["id"])
    try:
        raw_reviews, grouped = fetch_okendo_latest_reviews(
            product_id, count=LATEST_REVIEW_COUNT
        )
    except requests.RequestException:
        raw_reviews, grouped = [], False
    return build_product_full(handle, data, raw_reviews, grouped)
