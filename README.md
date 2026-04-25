# AI-Ready Product Catalog – Take Home Submission

This repo is a **FastAPI** backend (scrape, ACP/DeepSeek) plus a **Vite + React** web UI. Follow the steps below to run everything on your machine.

## Running from scratch

### What you need

- **Python** 3.10+ (3.12 recommended)
- **Node.js** 20+ and npm
- A **DeepSeek** API key ([DeepSeek](https://www.deepseek.com/)) for live model calls. Without it, some endpoints still work (catalog scrape, product detail); ACP features that call DeepSeek return errors or use local fallbacks where implemented.

### 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd ccp-assement
```

### 2. Backend (FastAPI)

From the project root (`ccp-assement/`):

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit **`.env`** and set at least:

| Variable | Purpose |
|----------|---------|
| `DEEPSEEK_API_KEY` | Required for `POST /api/acp/convert-from-product-detail` and the bulk ACP path that calls DeepSeek |
| `DEEPSEEK_BASE_URL` | Default: `https://api.deepseek.com/v1` (OpenAI-compatible) |
| `DEEPSEEK_MODEL` | e.g. `deepseek-chat` |
| `MERCHANT_ID`, `MERCHANT_NAME` | Injected into prompts / fallback output |

Optional: copy **`.env.local`** over `.env` for machine-specific overrides (the app loads `.env` then `.env.local`).

Start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **OpenAPI / Swagger:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
- **Health:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 3. Web UI (Vite + React)

In a **second terminal** (with the API still running):

```bash
cd web
npm install
cp .env.example .env.local
```

Set **`VITE_API_BASE_URL`** in `web/.env.local` to your API origin **without a trailing slash** (default: `http://127.0.0.1:8000` — must match CORS: the API allows `http://localhost:5173` and common dev origins).

```bash
npm run dev
```

Open **[http://localhost:5173](http://localhost:5173)** — load the catalog, open a product’s API detail, then **Generate ACP JSON**.

### 4. Production build (optional)

```bash
cd web
npm run build
npm run preview   # serves the built app (check preview URL in the terminal)
```

The preview app still needs the API running separately unless you add a reverse proxy.

### 5. CORS

If the UI runs on a different origin, set **`CORS_ORIGINS`** in the root `.env` to a comma-separated list, e.g. `http://localhost:5173,http://127.0.0.1:5173`.

---

## Project write-up

For this assignment, I built a small service that takes product data from `getmainelobster.com`, converts it into a cleaner AI-ready catalog format, and exposes both versions for comparison.

The core idea I followed was simple:

Most merchant catalogs are built for humans browsing websites.  AI shopping agents need data built for reasoning.

That means raw titles, prices, and images are not enough. Agents need structured product attributes, clean pricing, fulfillment signals, and enough context to confidently recommend products.

So my focus was less on UI polish, and more on building a transformation pipeline that upgrades messy merchant data into something usable by AI systems.


My Approach

1. Product Extraction

Since the merchant is running on Shopify, I first looked for the fastest and most reliable extraction path.

Instead of scraping rendered HTML pages product-by-product, I used Shopify-compatible JSON sources where available, then used HTML fallback logic where needed.

This gave me:

- Faster extraction
- Cleaner product source data
- Less brittle selectors
- Easier repeatability

For each product, I captured:

- title
- url
- price
- image
- handle


2. Dual Representations

Each product is stored in two formats:

- Original

This stays as close to source data as possible.

Example:

json
{
  "title": "1 LB Jumbo Shrimp",
  "price": "$24.99",
  "url": "...",
  "image_url": "..."
}


- AI-Ready

This is the normalized version designed for agent consumption.

Example:

{
  "id": "prod_jumbo_shrimp",
  "title": "Jumbo Shrimp",
  "price": {
    "amount": 2499,
    "currency": "USD"
  },
  "attributes": {
    "category": "seafood",
    "weight": {
      "value": 1,
      "unit": "lb"
    }
  },
  "fulfillment": {
    "perishable": true,
    "cold_shipping_required": true
  }
}


Why I Chose OpenAI ACP Over Google UCP

I reviewed both ACP and UCP at a high level. I chose OpenAI’s ACP as the primary schema target for a few reasons.

1. More Actionable Commerce Direction

ACP feels more execution-oriented. It is centered around actual agent transactions:

* discovery
* selection
* checkout
* delegated purchasing
* fulfillment flow

That aligns well with this assignment because the end goal is not only “can AI understand this product?” but also “can AI confidently recommend and buy it?”

2. Stronger Product Object Requirements

ACP naturally pushes toward richer commerce objects such as:

* normalized price objects
* merchant identity
* availability
* fulfillment readiness
* structured attributes

That helped guide better schema decisions.



Minimum Viable Product Object for an AI Agent

Based on my research, an AI agent needs at minimum:

{
  "id": "unique_id",
  "title": "product name",
  "description": "clear summary",
  "price": {
    "amount": 2499,
    "currency": "USD"
  },
  "availability": "in_stock",
  "images": [],
  "merchant": {},
  "attributes": {},
  "fulfillment": {}
}


Without these fields, the agent has gaps in trust, comparability, or purchase confidence.



Key Decisions I Made

01. Use Structured Enrichment

Instead of only renaming fields, I transformed titles into usable attributes.

Example:

`1 Pint Lobster Bisque`

became:

* category: seafood
* subcategory: soup
* flavor: lobster bisque
* volume: 1 pint

That creates actual machine understanding.

02. Price Normalization

I converted string prices into cents + currency objects.

This avoids ambiguity and is much safer for downstream systems.

03. Fulfillment Signals

For seafood products, I added:

* perishable
* cold shipping required

These are highly relevant for recommendation confidence.

-----------------------------------------------------------------------------------

Tradeoffs I Made

01. I Prioritized Schema Quality Over Full Catalog Coverage

I targeted a smaller reliable subset instead of rushing full-site extraction with weak transforms.

02. I Used rules + AI Enrichment

Some attributes are inferred from titles rather than guaranteed from merchant source data.
That reflects real-world catalog normalization, where source data is often incomplete.

03. UI Is Functional, Not Fancy

I focused on making transformations obvious instead of styling.


What I Skipped and Why

01. Real-Time Inventory Sync - Out of scope for the time budget.

02. Variant Explosion Handling - Products with many sizes / pack combinations could be modeled deeper.

03. Protocol Submission Layer - I designed against ACP rather than integrating to a live registry.

04. Diff viewing - time budget was not enough for this.



What I’d Build Next With Another Week

1. Full Merchant Ingestion Pipeline

Handle any Shopify merchant automatically.

2. Confidence Scoring System

Show how certain the system is about inferred attributes.

3. Multi-Protocol Export Layer

Export:

* ACP
* UCP
* generic JSON-LD
* marketplace feeds

4. Better AI Comparison UI

Show exactly what was inferred vs sourced.

5. Scheduled Sync Jobs

Keep pricing and availability fresh.

Final Thought

The hardest part of this assignment was not scraping products. It was deciding what an AI agent actually needs in order to trust and recommend a product.That is where I spent most of my time: turning merchant data into decision-ready commerce data.
