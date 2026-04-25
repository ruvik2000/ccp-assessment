import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Load .env from project root before any `app` imports (those read os.environ at import time).
try:
    from dotenv import load_dotenv

    _ROOT = Path(__file__).resolve().parent.parent
    load_dotenv(_ROOT / ".env")
    load_dotenv(_ROOT / ".env.local", override=True)
except ImportError:
    pass

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.acp.schema import ACPFeedResponse, ACPFromDetailResponse
from app.enrichment import ProductFull, fetch_product_full
from app.scraper import Product, extract_catalog
from app.services.acp_feed import build_acp_feed_response
from app.services.acp_single_convert import convert_product_detail_body

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    stream=sys.stdout,
    force=True,
)
logging.getLogger("acp").setLevel(logging.INFO)
logging.getLogger("acp.deepseek").setLevel(logging.INFO)
logging.getLogger("acp.feed").setLevel(logging.INFO)

app = FastAPI(
    title="ACP product feed (Shopify + DeepSeek)",
    description="Catalog scrape, ACP feed via DeepSeek, local fallback. See POST /products/acp-feed.",
    version="0.2.0",
)

_cors = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
)
_cors_list = [o.strip() for o in _cors.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "message": "Welcome. See GET /api/scrape/catalog, GET /api/scrape/product/{handle}, POST /api/acp/convert-from-product-detail, POST /products/acp-feed",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/scrape/catalog", response_model=List[Product])
def get_catalog():
    """Scrapes the collection HTML and returns summary rows (includes product handle for detail API)."""
    return extract_catalog()


@app.get("/api/scrape/product/{handle}", response_model=ProductFull)
def get_product_full(handle: str):
    """Product detail: Shopify JSON, 10 latest Okendo reviews, shipping policy text."""
    return fetch_product_full(handle)


@app.post("/api/acp/convert-from-product-detail", response_model=ACPFromDetailResponse)
def post_acp_from_product_detail(body: Dict[str, Any] = Body(...)):
    """
    Client sends the same JSON as GET /api/scrape/product/{handle}.
    Returns the model-generated ACP JSON as-is (no server-side ACP schema validation or local fallback).
    """
    if not isinstance(body, dict) or not body:
        raise HTTPException(status_code=400, detail="Request body must be a non-empty JSON object")
    return convert_product_detail_body(body)


@app.post("/products/acp-feed", response_model=ACPFeedResponse)
def post_acp_feed():
    """
    1) Scrape catalog from the configured Shopify collection page.
    2) Enrich and normalize to ACP JSON via DeepSeek (if DEEPSEEK_API_KEY is set).
    3) Pydantic-validate; on mismatch or error, use deterministic local transformer.
    4) Return acp_feed + meta (tokens, latency, failures).
    """
    return build_acp_feed_response()
