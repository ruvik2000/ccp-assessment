"""
DeepSeek chat completions for ACP feed enrichment.
OpenAI-compatible: POST {base}/chat/completions
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, List, Optional

import requests

from app.acp.config import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    MERCHANT_ID,
    MERCHANT_NAME,
    DEFAULT_SHIPPING_REGIONS,
)


def _deepseek_api_key() -> str:
    """Read at call time so `load_dotenv()` in main runs before first use."""
    return (os.environ.get("DEEPSEEK_API_KEY") or "").strip()

logger = logging.getLogger("acp.deepseek")

REQUEST_TIMEOUT = 120
MAX_RETRIES = 2  # one retry after first failure
RATE_LIMIT_SLEEP = 2.0


@dataclass
class DeepSeekEnrichResult:
    acp_list: list[dict[str, Any]]
    success: bool
    error: Optional[str]
    latency_ms: int
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    raw_response_excerpt: Optional[str]
    rate_limited: bool
    retried: bool


def _system_merchant_hint() -> str:
    regions = ", ".join(DEFAULT_SHIPPING_REGIONS) or "US"
    return (
        f"Merchant id must be {MERCHANT_ID!r} and merchant name {MERCHANT_NAME!r} unless the input "
        f"clearly names another store. Default shipping_regions to [{json.dumps(DEFAULT_SHIPPING_REGIONS)}] "
        f"or {regions!r} split as a JSON array of region codes. "
    )


def _build_user_prompt(raw_json: str) -> str:
    return f"""Transform the following raw product JSON into ACP-compliant e-commerce feed JSON.

Rules:
- Return ONLY a single JSON object with a key "acp_feed" whose value is a JSON array of product objects. No other top-level keys.
- The acp_feed array MUST have exactly the same number of items as the input array, in the same order. One input row -> one output product.
- No markdown, no code fences, no explanation.
- Infer categories, subcategories, and attributes (weight, volume, packaging) from titles where possible.
- Convert prices to integer cents in price.amount; currency is ISO code (e.g. USD).
- Generate stable ids: "prod_" + a short slug from title + "_" + 6 char hex from sha256(title|url) — or equivalent deterministic scheme.
- Keep original product URLs and image URLs; put images in images array (never a single string field).
- Add merchant, fulfillment, availability, and agent_metadata on every product.
- If uncertain, use null for optional numeric fields.
- For seafood, frozen, or fresh food, set fulfillment.perishable true and fulfillment.cold_shipping_required true when appropriate.

{_system_merchant_hint()}

INPUT:
{raw_json}
"""


def _strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def _coerce_to_acp_list(parsed: Any) -> Optional[list[dict[str, Any]]]:
    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    if isinstance(parsed, dict):
        for key in ("acp_feed", "feed", "products", "items", "acp", "data"):
            v = parsed.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return None


def _parse_model_json(content: str) -> tuple[Optional[list[dict[str, Any]]], Optional[str]]:
    t = _strip_code_fences(content)
    if not t:
        return None, "empty model content"
    try:
        parsed = json.loads(t)
    except json.JSONDecodeError as e:
        m = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", t)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                return None, f"json decode: {e}"
        else:
            return None, f"json decode: {e}"
    arr = _coerce_to_acp_list(parsed)
    if not arr:
        return None, "no product array in response (expected acp_feed array or top-level array)"
    return arr, None


def _post_chat(user_prompt: str) -> requests.Response:
    url = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {_deepseek_api_key()}",
        "Content-Type": "application/json",
    }
    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You are a data transformation engine. Output only valid JSON as instructed."},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    return requests.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)


def enrich_products_with_deepseek(raw_products: list[dict[str, Any]]) -> DeepSeekEnrichResult:
    """
    Calls DeepSeek once; on JSON parse / transport failure, retries once.
    On 429, sleeps and retries. Does not raise on failure; returns success=False.
    """
    if not _deepseek_api_key():
        return DeepSeekEnrichResult(
            acp_list=[],
            success=False,
            error="DEEPSEEK_API_KEY is not set",
            latency_ms=0,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            raw_response_excerpt=None,
            rate_limited=False,
            retried=False,
        )

    raw_json = json.dumps(raw_products, ensure_ascii=False, indent=2)
    user_prompt = _build_user_prompt(raw_json)
    retried = False
    last_err: Optional[str] = None
    raw_excerpt: Optional[str] = None
    rate_limited = False

    for attempt in range(MAX_RETRIES):
        t0 = time.perf_counter()
        try:
            r = _post_chat(user_prompt)
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
        except requests.RequestException as e:
            last_err = str(e)
            logger.warning("deepseek request failed: %s", e, exc_info=False)
            if attempt + 1 < MAX_RETRIES:
                retried = True
                time.sleep(0.5)
                continue
            return DeepSeekEnrichResult(
                acp_list=[],
                success=False,
                error=last_err,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                raw_response_excerpt=last_err[:2000],
                rate_limited=False,
                retried=retried,
            )

        if r.status_code == 429:
            rate_limited = True
            logger.warning("deepseek 429: sleeping %.1fs (attempt %s)", RATE_LIMIT_SLEEP, attempt)
            time.sleep(RATE_LIMIT_SLEEP)
            if attempt + 1 < MAX_RETRIES:
                retried = True
                continue
            return DeepSeekEnrichResult(
                acp_list=[],
                success=False,
                error="rate_limited",
                latency_ms=elapsed_ms,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                raw_response_excerpt=r.text[:2000] if r.text else None,
                rate_limited=True,
                retried=retried,
            )

        if r.status_code >= 400:
            last_err = f"HTTP {r.status_code}: {r.text[:500]}"
            logger.error("deepseek error response: %s", last_err)
            if attempt + 1 < MAX_RETRIES:
                retried = True
                time.sleep(0.5)
                continue
            return DeepSeekEnrichResult(
                acp_list=[],
                success=False,
                error=last_err,
                latency_ms=elapsed_ms,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                raw_response_excerpt=r.text[:2000] if r.text else None,
                rate_limited=rate_limited,
                retried=retried,
            )

        try:
            data = r.json()
        except json.JSONDecodeError as e:
            last_err = f"response not json: {e}"
            if attempt + 1 < MAX_RETRIES:
                retried = True
                continue
            return DeepSeekEnrichResult(
                acp_list=[],
                success=False,
                error=last_err,
                latency_ms=elapsed_ms,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                raw_response_excerpt=r.text[:2000],
                rate_limited=rate_limited,
                retried=retried,
            )

        choice0 = (data.get("choices") or [{}])[0] or {}
        content = (choice0.get("message") or {}).get("content") or ""
        raw_excerpt = (content or "")[:2000]
        usage = data.get("usage") or {}
        pt = usage.get("prompt_tokens")
        ct = usage.get("completion_tokens")
        tt = usage.get("total_tokens")
        if pt is not None and ct is not None and tt is None:
            tt = int(pt) + int(ct) if isinstance(pt, (int, float)) and isinstance(ct, (int, float)) else None

        acp_list, perr = _parse_model_json(content)
        if acp_list is not None:
            logger.info(
                "deepseek ok: products=%s tokens=%s latency_ms=%s",
                len(acp_list),
                tt,
                elapsed_ms,
            )
            return DeepSeekEnrichResult(
                acp_list=acp_list,
                success=True,
                error=None,
                latency_ms=elapsed_ms,
                prompt_tokens=pt,
                completion_tokens=ct,
                total_tokens=tt,
                raw_response_excerpt=raw_excerpt,
                rate_limited=rate_limited,
                retried=retried,
            )

        last_err = perr or "parse_failed"
        logger.warning("deepseek parse failed: %s excerpt=%r", perr, raw_excerpt[:200])
        if attempt + 1 < MAX_RETRIES:
            retried = True
            time.sleep(0.5)
            continue
        return DeepSeekEnrichResult(
            acp_list=[],
            success=False,
            error=last_err,
            latency_ms=elapsed_ms,
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=tt,
            raw_response_excerpt=raw_excerpt,
            rate_limited=rate_limited,
            retried=retried,
        )

    return DeepSeekEnrichResult(
        acp_list=[],
        success=False,
        error=last_err or "unknown",
        latency_ms=0,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        raw_response_excerpt=raw_excerpt,
        rate_limited=rate_limited,
        retried=retried,
    )


@dataclass
class DeepSeekSingleAcpResult:
    acp: Optional[dict[str, Any]]
    success: bool
    error: Optional[str]
    latency_ms: int
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    rate_limited: bool
    retried: bool


def _build_single_product_prompt(raw_json: str) -> str:
    return f"""Transform the following product detail JSON (Shopify-style fields, reviews, policies) into ONE ACP-compliant product object.

Rules:
- Return ONLY a single JSON object with a key "acp" whose value is the one product. No other top-level keys.
- No markdown, no code fences, no explanation.
- REQUIRED keys inside acp: id, title, description (string), url (string, same as input url), price, images, attributes, availability, merchant, fulfillment, agent_metadata. Never omit "description" or "url".
- Use description_text for description when non-empty; otherwise summarize description_html. Keep it concise for agents.
- price.amount: integer minor units (cents). price.currency: e.g. USD.
- images: all image URL strings from the input.
- id: use pattern prod_<slug>_<6-hex> derived from title and url.
- Map variants into a sensible single price: prefer the first available variant or the default variant price.
- availability.status: in_stock or out_of_stock; quantity may be null.
- Add merchant, fulfillment, availability, and agent_metadata; infer perishable / cold_shipping for seafood, frozen, or fresh.
- You may add attributes.review_count from the reviews list length, and a short product_type-derived category.
- If uncertain, use null for optional numbers.

{_system_merchant_hint()}

INPUT:
{raw_json}
"""


def _parse_single_acp_object(content: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    t = _strip_code_fences(content)
    if not t:
        return None, "empty model content"
    try:
        parsed = json.loads(t)
    except json.JSONDecodeError as e:
        m = re.search(r"\{[\s\S]*\}", t)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                return None, f"json decode: {e}"
        else:
            return None, f"json decode: {e}"
    if isinstance(parsed, dict):
        v = parsed.get("acp")
        if isinstance(v, dict):
            return v, None
        if all(k in parsed for k in ("id", "title", "url", "price")):
            return parsed, None
        if len(parsed) > 0:
            return parsed, None
    return None, "expected a JSON object from the model"


def enrich_product_detail_to_acp(detail: dict[str, Any]) -> DeepSeekSingleAcpResult:
    if not _deepseek_api_key():
        return DeepSeekSingleAcpResult(
            acp=None,
            success=False,
            error="DEEPSEEK_API_KEY is not set",
            latency_ms=0,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            rate_limited=False,
            retried=False,
        )
    user_prompt = _build_single_product_prompt(json.dumps(detail, ensure_ascii=False, indent=2))
    retried = False
    last_err: Optional[str] = None
    raw_excerpt: Optional[str] = None
    rate_limited = False

    for attempt in range(MAX_RETRIES):
        t0 = time.perf_counter()
        try:
            r = _post_chat(user_prompt)
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
        except requests.RequestException as e:
            last_err = str(e)
            if attempt + 1 < MAX_RETRIES:
                retried = True
                time.sleep(0.5)
                continue
            return DeepSeekSingleAcpResult(
                acp=None,
                success=False,
                error=last_err,
                latency_ms=int((time.perf_counter() - t0) * 1000),
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                rate_limited=rate_limited,
                retried=retried,
            )

        if r.status_code == 429:
            rate_limited = True
            time.sleep(RATE_LIMIT_SLEEP)
            if attempt + 1 < MAX_RETRIES:
                retried = True
                continue
            return DeepSeekSingleAcpResult(
                acp=None,
                success=False,
                error="rate_limited",
                latency_ms=elapsed_ms,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                rate_limited=True,
                retried=retried,
            )

        if r.status_code >= 400:
            last_err = f"HTTP {r.status_code}: {r.text[:500]}"
            if attempt + 1 < MAX_RETRIES:
                retried = True
                time.sleep(0.5)
                continue
            return DeepSeekSingleAcpResult(
                acp=None,
                success=False,
                error=last_err,
                latency_ms=elapsed_ms,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                rate_limited=rate_limited,
                retried=retried,
            )

        try:
            data = r.json()
        except json.JSONDecodeError as e:
            last_err = f"response not json: {e}"
            if attempt + 1 < MAX_RETRIES:
                retried = True
                continue
            return DeepSeekSingleAcpResult(
                acp=None,
                success=False,
                error=last_err,
                latency_ms=elapsed_ms,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                rate_limited=rate_limited,
                retried=retried,
            )

        choice0 = (data.get("choices") or [{}])[0] or {}
        cont = (choice0.get("message") or {}).get("content") or ""
        raw_excerpt = (cont or "")[:2000]
        usage = data.get("usage") or {}
        pt = usage.get("prompt_tokens")
        ct = usage.get("completion_tokens")
        tt = usage.get("total_tokens")
        if pt is not None and ct is not None and tt is None:
            tt = int(pt) + int(ct) if isinstance(pt, (int, float)) and isinstance(ct, (int, float)) else None

        one, perr = _parse_single_acp_object(cont)
        if one is not None:
            return DeepSeekSingleAcpResult(
                acp=one,
                success=True,
                error=None,
                latency_ms=elapsed_ms,
                prompt_tokens=pt,
                completion_tokens=ct,
                total_tokens=tt,
                rate_limited=rate_limited,
                retried=retried,
            )

        last_err = perr or "parse_failed"
        if attempt + 1 < MAX_RETRIES:
            retried = True
            time.sleep(0.5)
            continue
        return DeepSeekSingleAcpResult(
            acp=None,
            success=False,
            error=last_err,
            latency_ms=elapsed_ms,
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=tt,
            rate_limited=rate_limited,
            retried=retried,
        )

    return DeepSeekSingleAcpResult(
        acp=None,
        success=False,
        error=last_err or "unknown",
        latency_ms=0,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        rate_limited=rate_limited,
        retried=retried,
    )
