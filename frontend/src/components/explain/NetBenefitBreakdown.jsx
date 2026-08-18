const rupees = (n) => `Rs ${Math.abs(Math.round(n ?? 0)).toLocaleString('en-IN')}`

/**
 * Line-item breakdown of a relocation's NetBenefit, so the money case is legible:
 *   + revenue at destination
 *   - revenue lost at source
 *   - relocation cost
 *   - operator time cost
 *   - opportunity cost
 *   = net benefit
 */
export default function NetBenefitBreakdown({ breakdown = {}, netBenefit = 0 }) {
  const items = [
    { label: 'Revenue at destination', value: breakdown.revenue_at_destination, positive: true },
    { label: 'Revenue lost at source', value: breakdown.revenue_lost_at_source, positive: false },
    { label: 'Relocation cost', value: breakdown.relocation_cost, positive: false },
    { label: 'Operator time cost', value: breakdown.operator_time_cost, positive: false },
    { label: 'Opportunity cost', value: breakdown.opportunity_cost, positive: false },
  ]

  return (
    <div className="space-y-1.5">
      {items.map((it) => (
        <div key={it.label} className="flex items-center justify-between text-sm">
          <span className="text-slate-600">{it.label}</span>
          <span className={`tabular-nums ${it.positive ? 'text-emerald-700' : 'text-slate-700'}`}>
            {it.positive ? '+ ' : '- '}
            {rupees(it.value)}
          </span>
        </div>
      ))}
      <div className="mt-1 flex items-center justify-between border-t border-slate-200 pt-2 text-sm font-semibold">
        <span>Net benefit</span>
        <span className={`tabular-nums ${netBenefit >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
          {netBenefit >= 0 ? '+ ' : '- '}
          {rupees(netBenefit)}
        </span>
      </div>
    </div>
  )
}
