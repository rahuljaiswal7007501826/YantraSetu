/**
 * Explainability widget: a horizontal bar per contributing factor.
 *   factors: [{ label, value (0..1), weight? (0..1) }]
 *
 * Reused by the Demand screen (4 factors) and later the Allocation screen
 * (7 factors). Shows both the factor's strength and, optionally, its weight,
 * so the "why" behind a score is legible at a glance.
 */
export default function FactorBars({ factors = [] }) {
  return (
    <div className="space-y-2.5">
      {factors.map((f) => {
        const pct = Math.max(0, Math.min(100, Math.round((f.value ?? 0) * 100)))
        return (
          <div key={f.label}>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-600">{f.label}</span>
              <span className="tabular-nums text-slate-500">
                {pct}%
                {f.weight != null && (
                  <span className="ml-1 text-slate-400">· weight {f.weight}</span>
                )}
              </span>
            </div>
            <div className="mt-1 h-2 rounded bg-slate-100">
              <div className="h-2 rounded bg-emerald-500" style={{ width: `${pct}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}
