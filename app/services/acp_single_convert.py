"""Convert ProductFull (dict) to a single ACP JSON object via DeepSeek — return model output as-is (no Pydantic / merge / local fallback)."""

from __future__ import annotations

import time
from typing import Any

from app.acp.schema import ACPFromDetailResponse, AcpFromDetailMeta
from app.services.deepseek_service import DeepSeekSingleAcpResult, enrich_product_detail_to_acp


def convert_product_detail_body(body: dict[str, Any]) -> ACPFromDetailResponse:
    t0 = time.perf_counter()
    ds: DeepSeekSingleAcpResult = enrich_product_detail_to_acp(body)
    total_ms = int((time.perf_counter() - t0) * 1000)

    if ds.success and ds.acp is not None:
        return ACPFromDetailResponse(
            acp=ds.acp,
            meta=AcpFromDetailMeta(
                source="deepseek",
                latency_ms=total_ms,
                deepseek_ms=ds.latency_ms,
                total_tokens=ds.total_tokens,
                error=None,
                retried=ds.retried,
                rate_limited=ds.rate_limited,
            ),
        )

    return ACPFromDetailResponse(
        acp=None,
        meta=AcpFromDetailMeta(
            source="error",
            latency_ms=total_ms,
            deepseek_ms=ds.latency_ms if ds.latency_ms else None,
            total_tokens=ds.total_tokens,
            error=ds.error,
            retried=ds.retried,
            rate_limited=ds.rate_limited,
        ),
    )
