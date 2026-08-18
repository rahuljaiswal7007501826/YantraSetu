import { Activity, Coins, Gauge, PauseCircle, TrendingUp, Users } from 'lucide-react'

import BeforeAfter from '../components/analytics/BeforeAfter'
import CoverageChart from '../components/analytics/CoverageChart'
import UtilizationChart from '../components/analytics/UtilizationChart'
import Card from '../components/ui/Card'
import KpiCard from '../components/ui/KpiCard'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import {
  useAnalyticsImpact,
  useAnalyticsSummary,
  useAnalyticsUtilization,
} from '../hooks/useAnalytics'

const rupees = (n) => `Rs ${Math.round(n ?? 0).toLocaleString('en-IN')}`

export default function AnalyticsPage() {
  const summaryQ = useAnalyticsSummary()
  const impactQ = useAnalyticsImpact()
  const utilQ = useAnalyticsUtilization()

  // Summary + impact drive the KPIs and the hero; utilization feeds its own chart.
  const loading = summaryQ.isLoading || impactQ.isLoading
  const error = summaryQ.error || impactQ.error
  const refetchAll = () => {
    summaryQ.refetch()
    impactQ.refetch()
    utilQ.refetch()
  }

  const s = summaryQ.data
  const impact = impactQ.data

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Analytics</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          The measurable impact of YantraSetu&apos;s decisions — computed from real network data.
        </p>
      </header>

      {error ? (
        <ErrorState message={error?.message || 'Failed to load analytics.'} onRetry={refetchAll} />
      ) : loading || !s || !impact ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : (
        <>
          {/* Top KPI strip */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <KpiCard label="Network Efficiency" value={s.network_efficiency_score} hint="score / 100" icon={Gauge} accent="emerald" />
            <KpiCard label="Utilization" value={`${s.network_utilization_pct}%`} icon={TrendingUp} accent="blue" />
            <KpiCard label="Demand Coverage" value={`${s.demand_coverage_pct}%`} icon={Activity} accent="amber" />
            <KpiCard label="Idle Hours" value={s.total_idle_hours} icon={PauseCircle} accent="slate" />
            <KpiCard label="Additional Farmers" value={impact.additional_farmers_served} hint="served via relocation" icon={Users} accent="emerald" />
            <KpiCard label="Net Benefit" value={rupees(s.net_benefit)} hint="from relocations" icon={Coins} accent="emerald" />
          </div>

          {/* Hero: before -> action -> after */}
          <BeforeAfter impact={impact} />

          {/* Charts */}
          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="Utilization by CHC" subtitle="Utilization % per centre (busiest first)">
              <UtilizationChart
                data={utilQ.data?.per_chc}
                loading={utilQ.isLoading}
                error={utilQ.error}
                onRetry={utilQ.refetch}
              />
            </Card>
            <Card title="Demand Coverage" subtitle="Served vs awaiting requests">
              <CoverageChart summary={s} />
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
