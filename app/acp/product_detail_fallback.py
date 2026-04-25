"""Map ProductFull JSON (dict) to a single ACP product without AI."""

from __future__ import annotations

from typing import Any, List, Optional

from app.acp.fallback import _deterministic_id, _infer_attributes, _keywords, _perishable_flags, _parse_price_cents
from app.acp.config import DEFAULT_SHIPPING_REGIONS, MERCHANT_ID, MERCHANT_NAME
from app.acp.schema import ACPPrice, ACPProduct, AgentMetadata, Availability, FulfillmentBlock, MerchantBlock


def _first_variant_price_str(d: dict[str, Any]) -> Optional[str]:
    vs = d.get("variants")
    if not isinstance(vs, list) or not vs:
        return None
    v0 = vs[0]
    if not isinstance(v0, dict):
        return None
    p = v0.get("price")
    return str(p) if p is not None else None


def _any_available(d: dict[str, Any]) -> bool:
    vs = d.get("variants")
    if not isinstance(vs, list) or not vs:
        return True
    return any(isinstance(v, dict) and v.get("available", True) for v in vs)


def acp_from_product_detail_dict(d: dict[str, Any]) -> ACPProduct:
    title = str(d.get("title") or "Product").strip()
    url = str(d.get("url") or "")
    desc = str(d.get("description_text") or "").strip()
    if not desc:
        # fallback: strip html if any
        h = d.get("description_html")
        if isinstance(h, str) and h.strip():
            desc = h[:2000] + ("…" if len(h) > 2000 else "")

    if not desc:
        desc = f"{title}. Product detail from store API."

    price_s = _first_variant_price_str(d)
    cents, cur = _parse_price_cents(price_s)

    images: List[str] = []
    for im in d.get("images") or []:
        if isinstance(im, str) and im.strip():
            u = im.strip()
            if u.startswith("//"):
                u = "https:" + u
            images.append(u)

    attrs = _infer_attributes(title)
    ptype = d.get("product_type") or d.get("type")
    if ptype:
        attrs["shopify_type"] = str(ptype)
    if d.get("vendor"):
        attrs["vendor"] = str(d["vendor"])
    tags = d.get("tags")
    if isinstance(tags, list) and tags:
        attrs["shopify_tags"] = [str(t) for t in tags[:20]]
    revs = d.get("reviews")
    if isinstance(revs, list):
        attrs["review_sample_count"] = min(len(revs), 10_000)
    if d.get("shipping_policy_text"):
        pol = str(d.get("shipping_policy_text"))
        attrs["store_shipping_policy_excerpt"] = pol[:500] + ("…" if len(pol) > 500 else "")

    per, cold = _perishable_flags(title)
    in_stock = _any_available(d)
    kws = _keywords(title)
    if isinstance(tags, list):
        for t in tags:
            s = str(t).lower()
            if s and s not in kws and len(kws) < 20:
                kws.append(s)

    return ACPProduct(
        id=_deterministic_id(title, url),
        title=title,
        description=desc[:10_000],
        url=url,
        price=ACPPrice(amount=cents, currency=cur or "USD"),
        images=images,
        attributes=attrs,
        availability=Availability(
            status="in_stock" if in_stock else "out_of_stock",
            quantity=None,
        ),
        merchant=MerchantBlock(id=MERCHANT_ID, name=MERCHANT_NAME),
        fulfillment=FulfillmentBlock(
            shipping_regions=list(DEFAULT_SHIPPING_REGIONS) or ["US"],
            estimated_days=None,
            perishable=per,
            cold_shipping_required=cold,
        ),
        agent_metadata=AgentMetadata(
            search_keywords=sorted(kws)[:16],
            confidence_score=0.74,
        ),
    )
