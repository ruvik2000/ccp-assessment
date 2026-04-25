import { useMemo, useState } from 'react'

type Props = {
  value: unknown
  title: string
  emptyMessage?: string
  'aria-label'?: string
}

export function JsonBlock({ value, title, emptyMessage = 'Nothing to show yet.', 'aria-label': ariaLabel }: Props) {
  const [copied, setCopied] = useState(false)
  const text = useMemo(() => {
    if (value === undefined || value === null) return ''
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }, [value])

  const hasData = text.length > 0

  const copy = async () => {
    if (!hasData) return
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col rounded-xl border border-slate-200 bg-white shadow-sm" aria-label={ariaLabel ?? title}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
        <button
          type="button"
          onClick={copy}
          disabled={!hasData}
          className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {copied ? 'Copied' : 'Copy JSON'}
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-4">
        {!hasData ? (
          <p className="text-sm text-slate-500">{emptyMessage}</p>
        ) : (
          <pre className="font-mono text-xs leading-relaxed text-slate-800">{text}</pre>
        )}
      </div>
    </section>
  )
}
