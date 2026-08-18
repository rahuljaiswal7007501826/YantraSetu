import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import EmptyState from '../states/EmptyState'
import ErrorState from '../states/ErrorState'
import { SkeletonCard } from '../states/Loading'

/**
 * Horizontal bar chart of utilization % per CHC (from /api/analytics/utilization).
 * Data-driven only; sorted busiest-first so under-utilized centres sit at the
 * bottom - the ones worth rebalancing.
 */
export default function UtilizationChart({ data, loading, error, onRetry }) {
  if (error) {
    return <ErrorState message={error?.message || 'Failed to load utilization.'} onRetry={onRetry} />
  }
  if (loading || !data) return <SkeletonCard />

  const rows = [...data].sort((a, b) => b.utilization_pct - a.utilization_pct)
  if (rows.length === 0) {
    return <EmptyState title="No utilization data" description="No centres to display yet." />
  }

  return (
    <div className="h-[360px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 8 }}>
          <CartesianGrid horizontal={false} stroke="#f1f5f9" />
          <XAxis
            type="number"
            domain={[0, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 12, fill: '#64748b' }}
          />
          <YAxis
            type="category"
            dataKey="chc_name"
            width={150}
            tick={{ fontSize: 11, fill: '#334155' }}
          />
          <Tooltip cursor={{ fill: '#f8fafc' }} content={<UtilizationTooltip />} />
          <Bar dataKey="utilization_pct" fill="#10b981" radius={[0, 4, 4, 0]} name="Utilization %" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function UtilizationTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-2.5 text-xs shadow-md">
      <div className="font-semibold text-slate-800">{d.chc_name}</div>
      <div className="mt-1 text-slate-600">
        Utilization: <b>{d.utilization_pct}%</b>
      </div>
      <div className="text-slate-500">
        {d.active_hours} active / {d.schedulable_hours} schedulable h
      </div>
      <div className="text-slate-500">
        {d.machine_count} machines · {d.idle_hours} idle h
      </div>
    </div>
  )
}
