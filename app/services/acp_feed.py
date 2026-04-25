"""Scrape -> DeepSeek ACP -> validate; fallback to local transformer."""

from __future__ import annotations

import logging
import time
from typing import Any, List

from app.acp.fallback import build_acp_feed_local
from app.acp.schema import ACPFeedResponse, ACPProduct, FeedMeta
from app.scraper import Product, extract_catalog
from app.services.deepseek_service import enrich_products_with_deepseek

logger = logging.getLogger("acp.feed")


def _row_dicts_from_products(products: List[Product]) -> list[dict[str, Any]]:
    return [p.model_dump(mode="json", exclude_none=True) for p in products]


def _validate_acp_list(raw: list[dict[str, Any]]) -> list[ACPProduct]:
    out: list[ACPProduct] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        try:
            out.append(ACPProduct.model_validate(item))
        except Exception as e:
            logger.debug("acp product %s failed validation: %s", i, e)
    return out


def build_acp_feed_response(raw_catalog: List[Product] | None = None) -> ACPFeedResponse:
    t0 = time.perf_counter()
    products = list(raw_catalog) if raw_catalog is not None else extract_catalog()
    rows = _row_dicts_from_products(products)
    n = len(rows)

    ds = enrich_products_with_deepseek(rows)
    used_fallback = False
    err: str | None = ds.error
    source = "deepseek"
    acp_out: list[ACPProduct] = []

    if n == 0:
        total_ms = int((time.perf_counter() - t0) * 1000)
        return ACPFeedResponse(
            acp_feed=[],
            meta=FeedMeta(
                source="local_only",
                latency_ms=total_ms,
                deepseek_ms=ds.latency_ms if ds.latency_ms else None,
                prompt_tokens=ds.prompt_tokens,
                completion_tokens=ds.completion_tokens,
                total_tokens=ds.total_tokens,
                used_fallback=True,
                raw_products_count=0,
                acp_products_count=0,
                error=err or "empty catalog",
                retried=ds.retried,
                rate_limited=ds.rate_limited,
            ),
        )

    if ds.success and ds.acp_list and len(ds.acp_list) == n:
        acp_out = _validate_acp_list(ds.acp_list)
        if len(acp_out) == n:
            source = "deepseek" if not ds.retried else "deepseek_retry"
        else:
            logger.warning("ACP: AI returned %s rows, only %s valid; using local feed", n, len(acp_out))
            acp_out = build_acp_feed_local(rows)
            used_fallback = True
            source = "local_fallback"
            err = (err or "") + " | validation_mismatch" if err else "validation_mismatch"
    else:
        if not ds.acp_list and ds.error:
            logger.info("DeepSeek not used or failed: %s; using local ACP", ds.error)
        elif ds.acp_list and len(ds.acp_list) != n:
            logger.warning("DeepSeek count mismatch: expected %s got %s; using local", n, len(ds.acp_list))
            err = f"count_mismatch expected={n} got={len(ds.acp_list)}"
        else:
            err = err or "deepseek_unusable"
        acp_out = build_acp_feed_local(rows)
        used_fallback = True
        source = "local_fallback"

    # Never return empty if we have raw rows (local always produces n items)
    if len(acp_out) != n and n > 0:
        acp_out = build_acp_feed_local(rows)
        used_fallback = True
        source = "local_fallback"
        err = (err or "") + " | length_repair" if err else "length_repair"

    total_ms = int((time.perf_counter() - t0) * 1000)
    meta = FeedMeta(
        source=source,
        latency_ms=total_ms,
        deepseek_ms=ds.latency_ms if ds.latency_ms else None,
        prompt_tokens=ds.prompt_tokens,
        completion_tokens=ds.completion_tokens,
        total_tokens=ds.total_tokens,
        used_fallback=used_fallback,
        raw_products_count=n,
        acp_products_count=len(acp_out),
        error=err if (used_fallback and err) or (not acp_out and err) else None,
        retried=ds.retried,
        rate_limited=ds.rate_limited,
    )
    if source == "deepseek" and not used_fallback:
        meta.error = None

    logger.info(
        "acp_feed done: source=%s products=%s latency_ms=%s deepseek_ms=%s tokens=%s fallback=%s",
        source,
        len(acp_out),
        total_ms,
        meta.deepseek_ms,
        meta.total_tokens,
        used_fallback,
    )

    return ACPFeedResponse(acp_feed=acp_out, meta=meta)
