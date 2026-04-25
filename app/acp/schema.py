from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class ACPPrice(BaseModel):
    amount: int  # minor units, e.g. cents
    currency: str = "USD"

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_non_negative_cents(cls, v: Any) -> int:
        if v is None:
            return 0
        if isinstance(v, bool):
            raise ValueError("invalid amount")
        if isinstance(v, float):
            v = int(round(v))
        if isinstance(v, str) and v.strip().isdigit():
            v = int(v)
        v = int(v)  # type: ignore[arg-type]
        if v < 0:
            raise ValueError("amount must be >= 0")
        return v


class Availability(BaseModel):
    status: str = "in_stock"
    quantity: Optional[int] = None

    @field_validator("status")
    @classmethod
    def normalize_status(cls, v: str) -> str:
        return (v or "in_stock").lower().replace(" ", "_")


class MerchantBlock(BaseModel):
    id: str
    name: str


class FulfillmentBlock(BaseModel):
    shipping_regions: List[str] = Field(default_factory=lambda: ["US"])
    estimated_days: Optional[int] = None
    perishable: bool = True
    cold_shipping_required: bool = True

    @field_validator("shipping_regions", mode="before")
    @classmethod
    def coerce_regions(cls, v: Any) -> list:
        if v is None:
            return ["US"]
        if isinstance(v, str):
            return [v.strip()] if v.strip() else ["US"]
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()] or ["US"]
        return ["US"]


class AgentMetadata(BaseModel):
    search_keywords: List[str] = Field(default_factory=list)
    confidence_score: float = Field(0.85, ge=0.0, le=1.0)

    @field_validator("search_keywords", mode="before")
    @classmethod
    def coerce_keywords(cls, v: Any) -> list:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        if isinstance(v, list):
            return [str(x) for x in v]
        return []

    @field_validator("confidence_score", mode="before")
    @classmethod
    def coerce_confidence(cls, v: Any) -> float:
        if v is None:
            return 0.85
        return float(v)


class ACPProduct(BaseModel):
    """Agentic Commerce Protocol — normalized product for agents."""

    model_config = {"extra": "ignore"}

    id: str
    title: str
    description: str
    url: str

    @field_validator("title", mode="before")
    @classmethod
    def default_title(cls, v: Any) -> str:
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return "Unknown product"
        return str(v).strip()

    @field_validator("description", mode="before")
    @classmethod
    def default_description(cls, v: Any) -> str:
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return "Product from merchant catalog."
        return str(v).strip()
    price: ACPPrice
    images: List[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    availability: Availability = Field(default_factory=Availability)
    merchant: MerchantBlock
    fulfillment: FulfillmentBlock = Field(default_factory=FulfillmentBlock)
    agent_metadata: AgentMetadata = Field(default_factory=AgentMetadata)

    @field_validator("url", mode="before")
    @classmethod
    def ensure_url_str(cls, v: Any) -> str:
        return str(v or "").strip()

    @field_validator("id", mode="before")
    @classmethod
    def ensure_id_str(cls, v: Any) -> str:
        s = str(v or "").strip()
        if not s:
            return "prod_unknown"
        return s

    @field_validator("images", mode="before")
    @classmethod
    def coalesce_images(cls, v: Any) -> list:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return []


class FeedMeta(BaseModel):
    source: str  # "deepseek" | "deepseek_retry" | "local_fallback" | "local_only"
    latency_ms: int = 0
    deepseek_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    used_fallback: bool = False
    raw_products_count: int = 0
    acp_products_count: int = 0
    error: Optional[str] = None
    retried: bool = False
    rate_limited: bool = False


class ACPFeedResponse(BaseModel):
    acp_feed: List[ACPProduct]
    meta: FeedMeta


class AcpFromDetailMeta(BaseModel):
    """Metadata for single-product ACP (model output only; no server-side ACP schema validation)."""

    source: str  # "deepseek" | "error"
    latency_ms: int = 0
    deepseek_ms: Optional[int] = None
    total_tokens: Optional[int] = None
    error: Optional[str] = None
    retried: bool = False
    rate_limited: bool = False


class ACPFromDetailResponse(BaseModel):
    """Single product: raw ACP-shaped JSON from the model, or null if the call/parse failed."""

    acp: Optional[dict[str, Any]] = None
    meta: AcpFromDetailMeta
