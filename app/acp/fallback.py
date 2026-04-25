"""Deterministic ACP transform when DeepSeek is unavailable or returns invalid JSON."""

from __future__ import annotations

import hashlib
import re
from typing import Any, List

from app.acp.config import DEFAULT_SHIPPING_REGIONS, MERCHANT_ID, MERCHANT_NAME
from app.acp.schema import ACPPrice, ACPProduct, AgentMetadata, Availability, FulfillmentBlock, MerchantBlock


_SEAFOOD_KEYWORDS = re.compile(
    r"\b(lobster|shrimp|crab|fish|seafood|mussel|clam|oyster|scallop|bivalve|"
    r"bisque|chowder|sushi|roe|caviar|perch|tuna|salmon|halibut|chowdah|maine)\b",
    re.IGNORECASE,
)
_FROZEN_KEYWORDS = re.compile(r"\b(frozen|ice|dry\s*ice|chilled|fresh)\b", re.IGNORECASE)
_VOLUME_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(pint|pints|pt|gallon|gal|quart|qt|oz|ounce|ounces|lb|lbs|pound|pounds|gram|g|kg|ml|l|liter|litre)s?\b",
    re.IGNORECASE,
)
_WEIGHT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(oz|ounce|ounces|lb|lbs|pound|pounds|g|gram|grams|kg)\b",
    re.IGNORECASE,
)


def _slug_bits(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (title or "").lower()).strip("_")
    return s[:40] if s else "item"


def _deterministic_id(title: str, url: str) -> str:
    h = hashlib.sha256(f"{title}|{url}".encode("utf-8")).hexdigest()[:6]
    return f"prod_{_slug_bits(title)}_{h}"


def _parse_price_cents(raw: str | None) -> tuple[int, str]:
    if not raw:
        return 0, "USD"
    m = re.search(r"\$?([\d,]+)\.(\d{2})\b", raw.replace(",", ""))
    if m:
        major = int(m.group(1).replace(",", ""))
        minor = int(m.group(2))
        return major * 100 + minor, "USD"
    m2 = re.search(r"\$?(\d+)", raw.replace(",", ""))
    if m2:
        return int(m2.group(1)) * 100, "USD"
    return 0, "USD"


def _description_from_row(title: str) -> str:
    return f"{title.strip()}. Sourced from merchant catalog. Suitable for agent comparison and purchase flows."


def _infer_attributes(title: str) -> dict[str, Any]:
    t = (title or "").lower()
    out: dict[str, Any] = {"category": "gourmet_food", "subcategory": "specialty_items"}

    if _SEAFOOD_KEYWORDS.search(title or ""):
        out["category"] = "seafood"
        m = re.search(
            r"(lobster|shrimp|crab|fish|mussel|clam|oyster|scallop|salmon|tuna|chowder|bisque|tail|tails?)",
            t,
        )
        out["subcategory"] = m.group(1) if m else "seafood"

    vol = _VOLUME_RE.search(title or "")
    if vol:
        val, unit = vol.group(1), vol.group(2).lower()
        u = "lb" if unit in ("lb", "lbs", "pound", "pounds") else (
            "oz" if "ounce" in unit or unit in ("oz",) else "pint" if "pint" in unit else unit
        )
        if u in ("pint", "pt", "pints"):
            out["volume"] = {"value": float(val), "unit": "pint"}
        elif u in ("oz",) or "ounce" in unit:
            out["weight"] = {"value": float(val), "unit": "oz"}
        elif u == "lb":
            out["weight"] = {"value": float(val), "unit": "lb"}

    wt = _WEIGHT_RE.search(title or "")
    if "weight" not in out and wt:
        u = wt.group(2).lower()
        u_norm = "lb" if u in ("lb", "lbs", "pound", "pounds") else "g" if u in ("g", "gram", "grams") else "oz"
        out["weight"] = {"value": float(wt.group(1)), "unit": u_norm}

    if _FROZEN_KEYWORDS.search(title or ""):
        out["packaging"] = "frozen"
    else:
        out["packaging"] = "refrigerated_or_frozen" if _SEAFOOD_KEYWORDS.search(title or "") else "standard"

    return out


def _perishable_flags(title: str) -> tuple[bool, bool]:
    t = title or ""
    sea = bool(_SEAFOOD_KEYWORDS.search(t))
    froz = bool(_FROZEN_KEYWORDS.search(t)) or "frozen" in t.lower()
    if sea or froz:
        return True, True
    return False, False


def _keywords(title: str) -> List[str]:
    base = re.split(r"[^\w]+", (title or "").lower())
    return sorted({b for b in base if len(b) > 2} | {w for w in ("seafood", "gourmet", "lobster", "maine") if w in (title or "").lower()})


def acp_from_raw_row(row: dict[str, Any]) -> ACPProduct:
    title = str(row.get("title") or "Unknown").strip()
    url = str(row.get("url") or "")
    image_url = row.get("image_url")
    price_str = row.get("price")
    cents, cur = _parse_price_cents(str(price_str) if price_str else None)
    img_list: List[str] = []
    if image_url:
        u = str(image_url).strip()
        if u.startswith("//"):
            u = "https:" + u
        if u:
            img_list = [u]

    per, cold = _perishable_flags(title)

    return ACPProduct(
        id=_deterministic_id(title, url),
        title=title,
        description=_description_from_row(title),
        url=url,
        price=ACPPrice(amount=cents, currency=cur or "USD"),
        images=img_list,
        attributes=_infer_attributes(title),
        availability=Availability(status="in_stock", quantity=None),
        merchant=MerchantBlock(id=MERCHANT_ID, name=MERCHANT_NAME),
        fulfillment=FulfillmentBlock(
            shipping_regions=list(DEFAULT_SHIPPING_REGIONS) or ["US"],
            estimated_days=None,
            perishable=per,
            cold_shipping_required=cold,
        ),
        agent_metadata=AgentMetadata(
            search_keywords=_keywords(title)[:12],
            confidence_score=0.72,
        ),
    )


def build_acp_feed_local(raw_products: list[dict[str, Any]]) -> list[ACPProduct]:
    return [acp_from_raw_row(r) for r in raw_products]
