import { useCallback, useEffect, useState } from 'react'
import { checkHealth, convertProductDetailToAcp, fetchCatalog, fetchProductDetail, getApiBase } from './api'
import { CatalogTable } from './components/CatalogTable'
import { JsonBlock } from './components/JsonBlock'
import { ProductDetailDrawer } from './components/ProductDetailDrawer'
import type { AcpFromDetailResponse, CatalogRow } from './types'

type View = 'table' | 'raw'

export default function App() {
  const [health, setHealth] = useState<'unknown' | 'ok' | 'bad'>('unknown')
  const [healthMsg, setHealthMsg] = useState<string | null>(null)

  const [catalog, setCatalog] = useState<CatalogRow[] | null>(null)
  const [catLoading, setCatLoading] = useState(false)
  const [catError, setCatError] = useState<string | null>(null)

  const [view, setView] = useState<View>('table')

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerTitle, setDrawerTitle] = useState('')
  const [drawerHandle, setDrawerHandle] = useState<string | null>(null)
  const [drawerPayload, setDrawerPayload] = useState<unknown | null>(null)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [drawerError, setDrawerError] = useState<string | null>(null)

  const [acpResult, setAcpResult] = useState<AcpFromDetailResponse | null>(null)
  const [acpLoading, setAcpLoading] = useState(false)
  const [acpError, setAcpError] = useState<string | null>(null)

  const apiBase = getApiBase()

  const probe = useCallback(async () => {
    setHealth('unknown')
    setHealthMsg(null)
    try {
      await checkHealth()
      setHealth('ok')
    } catch (e) {
      setHealth('bad')
      setHealthMsg(e instanceof Error ? e.message : 'Health check failed')
    }
  }, [])

  useEffect(() => {
    void probe()
  }, [probe])

  useEffect(() => {
    if (!drawerOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setDrawerOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [drawerOpen])

  const loadCatalog = async () => {
    setCatLoading(true)
    setCatError(null)
    try {
      const data = await fetchCatalog()
      setCatalog(data)
      setView('table')
    } catch (e) {
      setCatError(e instanceof Error ? e.message : 'Failed to load catalog')
      setCatalog(null)
    } finally {
      setCatLoading(false)
    }
  }

  const clearResults = () => {
    setCatalog(null)
    setCatError(null)
  }

  const openDetail = async (handle: string, title: string) => {
    setDrawerOpen(true)
    setDrawerTitle(title)
    setDrawerHandle(handle)
    setDrawerPayload(null)
    setDrawerError(null)
    setAcpResult(null)
    setAcpError(null)
    setDrawerLoading(true)
    try {
      const p = await fetchProductDetail(handle)
      setDrawerPayload(p)
    } catch (e) {
      setDrawerError(e instanceof Error ? e.message : 'Detail request failed')
    } finally {
      setDrawerLoading(false)
    }
  }

  const convertToAcp = async () => {
    if (!drawerPayload) return
    setAcpLoading(true)
    setAcpError(null)
    try {
      const r = await convertProductDetailToAcp(drawerPayload)
      setAcpResult(r)
    } catch (e) {
      setAcpError(e instanceof Error ? e.message : 'ACP conversion failed')
      setAcpResult(null)
    } finally {
      setAcpLoading(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-svh max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Catalog &amp; ACP</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-600">
            Load the catalog, open a product’s <strong>API detail</strong>, then <strong>Generate ACP JSON</strong> to show the
            model output.
          </p>
        </div>
        <div className="flex flex-col items-stretch gap-2 sm:items-end">
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <span className="font-medium text-slate-500">API</span>
            <code
              className="max-w-[min(100vw,22rem)] truncate rounded border border-slate-200 bg-slate-100 px-2 py-1 font-mono text-[11px] text-slate-800"
              title={apiBase}
            >
              {apiBase}
            </code>
            <button type="button" onClick={() => void probe()} className="shrink-0 text-indigo-600 hover:underline">
              Retry
            </button>
          </div>
          <div className="flex items-center gap-2">
            {health === 'ok' && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-900 ring-1 ring-emerald-200">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-600" />
                API reachable
              </span>
            )}
            {health === 'bad' && (
              <span className="max-w-sm rounded-lg bg-amber-50 px-2 py-1 text-xs text-amber-900 ring-1 ring-amber-200" title={healthMsg ?? ''}>
                API unreachable — start the backend and check CORS.
              </span>
            )}
            {health === 'unknown' && <span className="text-xs text-slate-500">Checking connection…</span>}
          </div>
        </div>
      </header>

      {health === 'bad' && healthMsg && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="status">
          <p className="font-medium">Could not reach the API at {apiBase}</p>
          <p className="mt-1 text-amber-900/90">
            Run <code className="rounded bg-amber-100/80 px-1 font-mono">uvicorn app.main:app --reload</code> and set{' '}
            <code className="font-mono">VITE_API_BASE_URL</code> in <code className="font-mono">web/.env</code> if needed.
          </p>
        </div>
      )}

      <section className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void loadCatalog()}
            disabled={catLoading}
            className="inline-flex items-center justify-center rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:cursor-wait disabled:opacity-60"
          >
            {catLoading ? 'Scraping catalog…' : 'Load catalog'}
          </button>
          <button
            type="button"
            onClick={clearResults}
            disabled={catLoading}
            className="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Clear catalog
          </button>
        </div>
        <p className="text-sm text-slate-500 sm:ml-auto sm:max-w-md">
          <code className="text-xs">GET /api/scrape/catalog</code> for rows; use <strong>API detail</strong> on a row for
          full data and ACP generation.
        </p>
      </section>

      {catError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">
          {catError}
        </div>
      )}

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-3">
        <div
          className="inline-flex w-fit gap-1 rounded-lg border border-slate-200 bg-slate-100 p-1"
          role="tablist"
          aria-label="Data view"
        >
          {(
            [
              ['table', 'Catalog'],
              ['raw', 'Raw JSON'],
            ] as const
          ).map(([k, label]) => (
            <button
              key={k}
              type="button"
              role="tab"
              aria-selected={view === k}
              onClick={() => setView(k)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                view === k ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="min-h-[min(60vh,720px)] flex-1" role="tabpanel">
          {view === 'table' && (
            <CatalogTable
              rows={catalog ?? []}
              onOpenDetail={openDetail}
              detailLoadingHandle={drawerLoading ? drawerHandle : null}
            />
          )}
          {view === 'raw' && (
            <JsonBlock
              value={catalog ?? []}
              title="Raw catalog (array)"
              emptyMessage="Run “Load catalog” first."
              aria-label="Raw catalog JSON"
            />
          )}
        </div>
      </div>

      <footer className="border-t border-slate-200 pt-6 text-center text-xs text-slate-500">
        ACP: <code className="font-mono">POST /api/acp/convert-from-product-detail</code> with the same body as the detail
        response. CORS: <code className="font-mono">CORS_ORIGINS</code> on the API. UI: <code className="font-mono">VITE_API_BASE_URL</code>.
      </footer>

      <ProductDetailDrawer
        open={drawerOpen}
        title={drawerTitle}
        apiPayload={drawerPayload}
        apiLoading={drawerLoading}
        apiError={drawerError}
        onClose={() => setDrawerOpen(false)}
        onConvertToAcp={() => void convertToAcp()}
        acpResult={acpResult}
        acpLoading={acpLoading}
        acpError={acpError}
      />
    </div>
  )
}
