import type { AcpFeedResponse, AcpFromDetailResponse, CatalogRow, ProductFull } from './types'

const DEFAULT_BASE = 'http://127.0.0.1:8000'

export function getApiBase(): string {
  const v = import.meta.env.VITE_API_BASE_URL as string | undefined
  return (v && v.replace(/\/$/, '')) || DEFAULT_BASE
}

function withTimeout(ms: number) {
  const c = new AbortController()
  const t = setTimeout(() => c.abort(), ms)
  return { signal: c.signal, clear: () => clearTimeout(t) }
}

async function parseOrThrow(res: Response, label: string): Promise<unknown> {
  const text = await res.text()
  if (!res.ok) {
    let detail = text.slice(0, 2000)
    try {
      const j = JSON.parse(text) as { detail?: string }
      if (typeof j.detail === 'string') detail = j.detail
    } catch {
      // ignore
    }
    throw new Error(`${label}: ${res.status} ${res.statusText}${detail ? ` — ${detail}` : ''}`)
  }
  if (!text) return null
  try {
    return JSON.parse(text) as unknown
  } catch {
    throw new Error(`${label}: response was not valid JSON`)
  }
}

export async function checkHealth(): Promise<{ status: string }> {
  const { signal, clear } = withTimeout(8000)
  try {
    const r = await fetch(`${getApiBase()}/api/health`, { signal })
    return (await parseOrThrow(r, 'Health check')) as { status: string }
  } finally {
    clear()
  }
}

export async function fetchCatalog(): Promise<CatalogRow[]> {
  const { signal, clear } = withTimeout(90_000)
  try {
    const r = await fetch(`${getApiBase()}/api/scrape/catalog`, { signal })
    const data = (await parseOrThrow(r, 'Catalog')) as CatalogRow[]
    return Array.isArray(data) ? data : []
  } finally {
    clear()
  }
}

export async function fetchAcpFeed(): Promise<AcpFeedResponse> {
  const { signal, clear } = withTimeout(180_000)
  try {
    const r = await fetch(`${getApiBase()}/products/acp-feed`, { method: 'POST', signal })
    return (await parseOrThrow(r, 'ACP feed')) as AcpFeedResponse
  } finally {
    clear()
  }
}

export async function fetchProductDetail(handle: string): Promise<ProductFull> {
  const h = encodeURIComponent(handle)
  const { signal, clear } = withTimeout(120_000)
  try {
    const r = await fetch(`${getApiBase()}/api/scrape/product/${h}`, { signal })
    return (await parseOrThrow(r, 'Product detail')) as ProductFull
  } finally {
    clear()
  }
}

export async function convertProductDetailToAcp(detail: unknown): Promise<AcpFromDetailResponse> {
  const { signal, clear } = withTimeout(180_000)
  try {
    const r = await fetch(`${getApiBase()}/api/acp/convert-from-product-detail`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(detail),
      signal,
    })
    return (await parseOrThrow(r, 'ACP convert')) as AcpFromDetailResponse
  } finally {
    clear()
  }
}
