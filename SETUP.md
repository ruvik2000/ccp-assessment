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
cd ccp-assessment
```

### 2. Backend (FastAPI)

From the project root (`ccp-assessment/`):

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

please contact if the deepseek api key is needed.

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