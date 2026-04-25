import { diffLines } from 'diff'

type Props = {
  left: unknown
  right: unknown
  leftLabel?: string
  rightLabel?: string
}

/**
 * Renders a unified line diff of two values pretty-printed as JSON.
 * Added lines (toward the right) are tinted green; removed (from left) red; unchanged neutral.
 */
export function JsonLineDiff({ left, right, leftLabel = 'API', rightLabel = 'ACP' }: Props) {
  const a = (() => {
    try {
      return JSON.stringify(left ?? null, null, 2)
    } catch {
      return String(left)
    }
  })()
  const b = (() => {
    try {
      return JSON.stringify(right ?? null, null, 2)
    } catch {
      return String(right)
    }
  })()
  const parts = diffLines(a, b, { ignoreWhitespace: false })

  return (
    <div
      className="rounded-lg border border-slate-200 bg-slate-50 font-mono text-xs leading-relaxed"
      role="region"
      aria-label={`Line diff: ${leftLabel} versus ${rightLabel}`}
    >
      <div className="flex border-b border-slate-200 bg-slate-100 px-2 py-1 text-[11px] text-slate-600">
        <span className="font-medium">Changes</span>
        <span className="ml-2 text-slate-500">
          ({leftLabel} → {rightLabel}, line-level; schemas differ, so this is a rough guide)
        </span>
      </div>
      <pre className="max-h-64 min-h-[4rem] overflow-auto whitespace-pre-wrap break-all p-3 text-left">
        {parts.map((p, i) => {
          if (p.added) {
            return (
              <span key={i} className="block bg-emerald-100/90 text-slate-900">
                {p.value}
              </span>
            )
          }
          if (p.removed) {
            return (
              <span key={i} className="block bg-rose-100/90 text-slate-900 line-through decoration-rose-500/50">
                {p.value}
              </span>
            )
          }
          return (
            <span key={i} className="block text-slate-800">
              {p.value}
            </span>
          )
        })}
      </pre>
    </div>
  )
}
