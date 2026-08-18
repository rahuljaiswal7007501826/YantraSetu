import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import EmptyState from '../states/EmptyState'

const COLORS = { Served: '#10b981', Awaiting: '#f59e0b', Cancelled: '#94a3b8' }
const LABELS = { Served: 'Served', Awaiting: 'Awaiting service', Cancelled: 'Cancelled' }

/**
 * Donut of request outcomes, derived entirely from the summary counts:
 *   Served    = served_requests
 *   Awaiting  = non_cancelled_requests - served_requests
 *   Cancelled = total_requests - non_cancelled_requests   (shown only if > 0)
 * Center shows demand_coverage_pct (served / non-cancelled).
 */
export default function CoverageChart({ summary }) {
  if (!summary) return null

  const served = summary.served_requests ?? 0
  const nonCancelled = summary.non_cancelled_requests ?? 0
  const total = summary.total_requests ?? 0
  const awaiting = Math.max(0, nonCancelled - served)
  const cancelled = Math.max(0, total - nonCancelled)

  const slices = [
    { name: 'Served', value: served },
    { name: 'Awaiting', value: awaiting },
    ...(cancelled > 0 ? [{ name: 'Cancelled', value: cancelled }] : []),
  ].filter((s) => s.value > 0)

  if (total === 0 || slices.length === 0) {
    return <EmptyState title="No requests yet" description="No demand requests to summarize." />
  }

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-around">
      <div className="relative h-56 w-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              dataKey="value"
              nameKey="name"
              innerRadius={62}
              outerRadius={90}
              paddingAngle={2}
              stroke="none"
            >
              {slices.map((s) => (
                <Cell key={s.name} fill={COLORS[s.name] || '#cbd5e1'} />
              ))}
            </Pie>
            <Tooltip content={<CoverageTooltip total={total} />} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-slate-900">{summary.demand_coverage_pct}%</span>
          <span className="text-xs text-slate-500">coverage</span>
        </div>
      </div>

      <div className="w-full max-w-[220px] space-y-2">
        {slices.map((s) => (
          <div key={s.name} className="flex items-center gap-2 text-sm">
            <span
              className="h-3 w-3 shrink-0 rounded-sm"
              style={{ backgroundColor: COLORS[s.name] || '#cbd5e1' }}
            />
            <span className="text-slate-700">{LABELS[s.name] || s.name}</span>
            <span className="ml-auto font-medium tabular-nums text-slate-900">{s.value}</span>
          </div>
        ))}
        <div className="border-t border-slate-100 pt-2 text-xs text-slate-500">
          {served} of {nonCancelled} non-cancelled requests served
        </div>
      </div>
    </div>
  )
}

function CoverageTooltip({ active, payload, total }) {
  if (!active || !payload?.length) return null
  const d = payload[0]
  const share = total ? Math.round((d.value / total) * 100) : 0
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-2 text-xs shadow-md">
      <span className="font-semibold text-slate-800">{LABELS[d.name] || d.name}</span>: {d.value} ({share}%)
    </div>
  )
}
