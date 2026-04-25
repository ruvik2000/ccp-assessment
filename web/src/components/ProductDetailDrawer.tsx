import { JsonBlock } from './JsonBlock'
import type { AcpFromDetailResponse } from '../types'

type Props = {
  open: boolean
  title: string
  apiPayload: unknown | null
  apiLoading: boolean
  apiError: string | null
  onClose: () => void
  onConvertToAcp: () => void
  acpResult: AcpFromDetailResponse | null
  acpLoading: boolean
  acpError: string | null
}

export function ProductDetailDrawer({
  open,
  title,
  apiPayload,
  apiLoading,
  apiError,
  onClose,
  onConvertToAcp,
  acpResult,
  acpLoading,
  acpError,
}: Props) {
  if (!open) return null

  const canConvert = !apiLoading && !apiError && apiPayload != null
  const metaErr = acpResult?.meta.source === 'error' ? acpResult.meta.error : null

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
      <button type="button" className="absolute inset-0 bg-black/40" aria-label="Close panel" onClick={onClose} />
      <div className="relative z-10 flex h-full w-full max-w-[min(100vw,110rem)] flex-col border-l border-slate-200 bg-white shadow-2xl">
        <div className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div>
            <h2 id="drawer-title" className="text-lg font-semibold text-slate-900">
              API detail → ACP
            </h2>
            <p className="mt-0.5 text-sm text-slate-600">{title}</p>
            <p className="mt-1 text-xs text-slate-500">
              Left: full FastAPI <code className="rounded bg-slate-100 px-1">/api/scrape/product</code> response. Right: model-generated ACP JSON
              (raw output, no server validation).
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
            aria-label="Close"
          >
            <span className="text-2xl leading-none">×</span>
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-4">
          <div className="mb-4 flex min-h-0 flex-col gap-4 lg:grid lg:grid-cols-2 lg:items-stretch lg:gap-4">
            <div className="flex min-h-[12rem] flex-col">
              {apiLoading && (
                <div className="flex items-center gap-2 text-sm text-slate-600" role="status" aria-live="polite">
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
                  Loading product detail (reviews + policies may take a while)…
                </div>
              )}
              {!apiLoading && apiError && <p className="text-sm text-red-700">{apiError}</p>}
              {!apiLoading && !apiError && (
                <JsonBlock value={apiPayload} title="API response (raw)" emptyMessage="No payload." aria-label="API response JSON" />
              )}
            </div>

            <div className="flex min-h-[12rem] flex-col gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={onConvertToAcp}
                  disabled={!canConvert || acpLoading}
                  className="inline-flex items-center justify-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {acpLoading ? 'Generating…' : 'Generate ACP JSON'}
                </button>
                {!canConvert && !apiLoading && <span className="text-xs text-slate-500">Load the API response first.</span>}
              </div>
              {acpError && <p className="text-sm text-red-700">{acpError}</p>}
              {metaErr && <p className="text-sm text-red-700">{metaErr}</p>}
              {!acpLoading && !acpError && !metaErr && !acpResult && (
                <p className="text-sm text-slate-500">Run generation to see the ACP JSON here.</p>
              )}
              {!acpLoading && !acpError && acpResult?.acp != null && (
                <div className="min-h-0 min-w-0 flex-1">
                  <JsonBlock value={acpResult.acp} title="ACP (model output)" emptyMessage="No JSON." aria-label="ACP JSON" />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
