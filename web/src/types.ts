export type CatalogRow = {
  title: string
  url: string
  price?: string | null
  image_url?: string | null
  handle?: string | null
}

export type AcpFeedResponse = {
  acp_feed: unknown[]
  meta: {
    source: string
    latency_ms: number
    deepseek_ms: number | null
    prompt_tokens: number | null
    completion_tokens: number | null
    total_tokens: number | null
    used_fallback: boolean
    raw_products_count: number
    acp_products_count: number
    error: string | null
    retried: boolean
    rate_limited: boolean
  }
}

export type ProductFull = Record<string, unknown>

export type AcpFromDetailMeta = {
  source: 'deepseek' | 'error'
  latency_ms: number
  deepseek_ms: number | null
  total_tokens: number | null
  error: string | null
  retried: boolean
  rate_limited: boolean
}

export type AcpFromDetailResponse = {
  acp: Record<string, unknown> | null
  meta: AcpFromDetailMeta
}
