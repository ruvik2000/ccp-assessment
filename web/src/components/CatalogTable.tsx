import { useMemo, useState } from 'react'
import type { CatalogRow } from '../types'

type Props = {
  rows: CatalogRow[]
  onOpenDetail: (handle: string, title: string) => void
  detailLoadingHandle: string | null
}

export function CatalogTable({ rows, onOpenDetail, detailLoadingHandle }: Props) {
  const [q, setQ] = useState('')

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return rows
    return rows.filter(
      (r) =>
        r.title.toLowerCase().includes(s) ||
        (r.handle && r.handle.toLowerCase().includes(s)) ||
        r.url.toLowerCase().includes(s) ||
        (r.price && r.price.toLowerCase().includes(s)),
    )
  }, [rows, q])

  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/80 p-8 text-center text-sm text-slate-600">
        <p className="font-medium text-slate-800">No catalog loaded</p>
        <p className="mt-1">Use <strong>Load catalog</strong> to scrape the collection page first.</p>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 p-3 sm:flex sm:items-center sm:justify-between sm:gap-3">
        <h2 className="px-1 text-sm font-semibold text-slate-800">Scraped products</h2>
        <div className="mt-2 flex items-center gap-2 sm:mt-0">
          <label className="sr-only" htmlFor="catalog-filter">
            Filter table
          </label>
          <input
            id="catalog-filter"
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter by title, handle, URL, price…"
            className="w-full min-w-0 flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
          />
          <span className="shrink-0 text-xs text-slate-500">
            {filtered.length} / {rows.length}
          </span>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full min-w-[640px] border-collapse text-left text-sm">
          <thead className="sticky top-0 z-10 bg-slate-100/95 text-xs uppercase tracking-wide text-slate-600 backdrop-blur">
            <tr>
              <th scope="col" className="px-3 py-2 font-medium">
                Product
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Price
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Handle
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-3 py-6 text-center text-slate-500">
                  No rows match this filter. Clear the search box to see all products.
                </td>
              </tr>
            ) : (
              filtered.map((r) => {
                const canDetail = Boolean(r.handle)
                const loading = detailLoadingHandle === r.handle
                return (
                  <tr key={r.url} className="border-t border-slate-100 odd:bg-slate-50/50">
                    <td className="px-3 py-2 align-top">
                      <div className="font-medium text-slate-900">{r.title}</div>
                      <a href={r.url} target="_blank" rel="noreferrer" className="text-xs text-indigo-600 hover:underline">
                        Open on store
                      </a>
                    </td>
                    <td className="px-3 py-2 align-top text-slate-700">{r.price ?? '—'}</td>
                    <td className="px-3 py-2 align-top font-mono text-xs text-slate-600">{r.handle ?? '—'}</td>
                    <td className="px-3 py-2 align-top">
                      <button
                        type="button"
                        disabled={!canDetail || loading}
                        onClick={() => r.handle && onOpenDetail(r.handle, r.title)}
                        className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:border-indigo-300 hover:text-indigo-800 disabled:cursor-not-allowed disabled:opacity-50"
                        title={!canDetail ? 'No product handle; cannot load details' : 'Full scrape + reviews + ACP source data'}
                      >
                        {loading ? 'Loading…' : 'API detail'}
                      </button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
