import { ArrowRight, Shuffle, Users } from 'lucide-react'

import RiskPill from '../ui/RiskPill'

const rupees = (n) => `Rs ${Math.round(n ?? 0).toLocaleString('en-IN')}`

/**
 * The hero of the analytics dashboard: BEFORE -> YantraSetu Action -> AFTER.
 * Everything is driven by the /api/analytics/impact response; nothing is
 * hardcoded. With zero approved relocations, BEFORE == AFTER and we say so.
 */
export default function BeforeAfter({ impact }) {
  if (!impact) return null
  const { before, after } = impact
  const acted = impact.relocations_executed > 0

  const utilDelta = Number((after.utilization_pct - before.utilization_pct).toFixed(1))
  const idleDelta = Number((after.idle_hours - before.idle_hours).toFixed(1))
  const critDelta = after.critical_shortages - before.critical_shortages

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      {/* Narrative */}
      <div className="mb-5 flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-emerald-600 text-white">
          <Shuffle size={18} />
        </span>
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Before &rarr; YantraSetu Action &rarr; After
          </h2>
          <p className="mt-0.5 text-sm text-slate-600">
            {acted
              ? `YantraSetu identified ${impact.relocations_executed} under-utilized machine${
                  impact.relocations_executed > 1 ? 's' : ''
                } and recommended relocation. Here is the measurable impact.`
              : 'No relocations approved yet — the network is at its baseline. Approve a recommendation to see the measurable before/after impact.'}
          </p>
        </div>
      </div>

      {/* BEFORE | ACTION | AFTER */}
      <div className="grid items-stretch gap-3 lg:grid-cols-[1fr_auto_1fr]">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <ColHeader tone="slate">Before</ColHeader>
          <div className="space-y-3">
            <Stat label="Utilization" value={`${before.utilization_pct}%`} />
            <Stat label="Idle hours" value={before.idle_hours} />
            <Stat label="Critical shortages" value={before.critical_shortages} />
          </div>
        </div>

        <div className="flex flex-col justify-center rounded-xl border border-emerald-200 bg-emerald-50 p-4 lg:w-60">
          <div className="flex items-center justify-center gap-1 text-emerald-700">
            <ArrowRight className="hidden lg:block" size={16} />
            <span className="text-xs font-semibold uppercase tracking-wide">YantraSetu Action</span>
            <ArrowRight className="hidden lg:block" size={16} />
          </div>
          <div className="mt-3 text-center">
            <div className="text-3xl font-bold text-emerald-700">{rupees(impact.net_benefit)}</div>
            <div className="text-xs text-slate-500">net benefit</div>
          </div>
          <div className="mt-3 space-y-1 text-center text-xs text-slate-600">
            <div className="flex items-center justify-center gap-1.5">
              <Shuffle size={12} /> {impact.relocations_executed} relocation
              {impact.relocations_executed !== 1 ? 's' : ''}
            </div>
            <div className="flex items-center justify-center gap-1.5">
              <Users size={12} /> {impact.additional_farmers_served} more farmers served
            </div>
            <div>
              revenue {rupees(impact.revenue_gained)} &minus; cost {rupees(impact.relocation_cost)}
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-emerald-200 bg-white p-4">
          <ColHeader tone="emerald">After</ColHeader>
          <div className="space-y-3">
            <Stat label="Utilization" value={`${after.utilization_pct}%`} delta={utilDelta} better="up" unit="pts" />
            <Stat label="Idle hours" value={after.idle_hours} delta={idleDelta} better="down" />
            <Stat label="Critical shortages" value={after.critical_shortages} delta={critDelta} better="down" />
          </div>
        </div>
      </div>

      {/* Shortage relief per destination */}
      {impact.shortage_deltas?.length > 0 && (
        <div className="mt-5">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Shortage relief
          </div>
          <div className="space-y-2">
            {impact.shortage_deltas.map((d, i) => (
              <ShortageReliefRow key={`${d.cluster}-${d.machine_type}-${i}`} d={d} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ColHeader({ tone, children }) {
  const cls = tone === 'emerald' ? 'text-emerald-700' : 'text-slate-500'
  return <div className={`mb-3 text-xs font-semibold uppercase tracking-wide ${cls}`}>{children}</div>
}

function Stat({ label, value, delta, better, unit }) {
  let deltaEl = null
  if (delta !== undefined) {
    if (delta === 0) {
      deltaEl = <span className="text-xs text-slate-400">no change</span>
    } else {
      const improved = better === 'up' ? delta > 0 : delta < 0
      const color = improved ? 'text-emerald-600' : 'text-red-600'
      const sign = delta > 0 ? '+' : ''
      deltaEl = (
        <span className={`text-xs font-medium ${color}`}>
          {sign}
          {delta}
          {unit ? ` ${unit}` : ''}
        </span>
      )
    }
  }
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="flex items-baseline gap-2">
        <span className="text-lg font-semibold text-slate-900">{value}</span>
        {deltaEl}
      </span>
    </div>
  )
}

function ShortageReliefRow({ d }) {
  const before = Math.round((d.shortage_probability_before ?? 0) * 100)
  const after = Math.round((d.shortage_probability_after ?? 0) * 100)
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-slate-800">
          {d.cluster} &middot; {d.machine_type}
        </span>
        <span className="flex items-center gap-2">
          <RiskPill level={d.risk_before} />
          <ArrowRight size={12} className="text-slate-400" />
          <RiskPill level={d.risk_after} />
        </span>
      </div>
      <div className="space-y-1">
        <ProbBar label="before" pct={before} color="bg-slate-400" />
        <ProbBar label="after" pct={after} color="bg-emerald-500" />
      </div>
    </div>
  )
}

function ProbBar({ label, pct, color }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-12 shrink-0 text-xs text-slate-400">{label}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
      </div>
      <span className="w-10 shrink-0 text-right text-xs tabular-nums text-slate-600">{pct}%</span>
    </div>
  )
}
