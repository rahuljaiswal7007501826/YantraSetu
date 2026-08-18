import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, AlertTriangle, Layers, Search, TrendingUp } from 'lucide-react'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import KpiCard from '../components/ui/KpiCard'
import RiskPill from '../components/ui/RiskPill'
import Table from '../components/ui/Table'
import FactorBars from '../components/explain/FactorBars'
import EmptyState from '../components/states/EmptyState'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import { useForecast } from '../hooks/useForecast'

const RISK_ORDER = { CRITICAL: 3, HIGH: 2, MEDIUM: 1, LOW: 0 }
const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'high', label: 'High risk+' },
  { key: 'critical', label: 'Critical' },
]

const COLUMNS = [
  { key: 'cluster', label: 'Cluster' },
  { key: 'machine_type', label: 'Machine type' },
  { key: 'demand_score', label: 'Score', align: 'right' },
  { key: 'risk_level', label: 'Risk' },
  { key: 'expected_requests', label: 'Expected', align: 'right' },
  { key: 'available_supply', label: 'Avail', align: 'right' },
  { key: 'shortage_probability', label: 'Shortage', align: 'right' },
]

export default function DemandPage() {
  const { data, isLoading, isError, error, refetch } = useForecast()
  const navigate = useNavigate()
  const [filter, setFilter] = useState('all')
  const [selectedId, setSelectedId] = useState(null)

  const insights = data ?? []

  const kpis = useMemo(() => {
    const critical = insights.filter((i) => i.risk_level === 'CRITICAL').length
    const highPlus = insights.filter((i) => RISK_ORDER[i.risk_level] >= 2).length
    const clusters = new Set(insights.map((i) => i.cluster)).size
    return { critical, highPlus, clusters, top: insights[0] }
  }, [insights])

  const rows = useMemo(() => {
    let r = insights
    if (filter === 'high') r = r.filter((i) => RISK_ORDER[i.risk_level] >= 2)
    if (filter === 'critical') r = r.filter((i) => i.risk_level === 'CRITICAL')
    return r.map((i) => ({ ...i, id: `${i.cluster}|${i.machine_type}` }))
  }, [insights, filter])

  useEffect(() => {
    if (rows.length && !rows.some((r) => r.id === selectedId)) {
      setSelectedId(rows[0].id)
    }
  }, [rows, selectedId])

  if (isLoading) return <LoadingView />
  if (isError) {
    return (
      <PageShell>
        <ErrorState message={error?.message || 'Failed to load demand data.'} onRetry={refetch} />
      </PageShell>
    )
  }

  const selected = rows.find((r) => r.id === selectedId) || rows[0] || null

  const renderCell = (row, col) => {
    if (col.key === 'risk_level') return <RiskPill level={row.risk_level} />
    if (col.key === 'shortage_probability') return `${Math.round(row.shortage_probability * 100)}%`
    return row[col.key]
  }

  return (
    <PageShell>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Critical shortages" value={kpis.critical} icon={AlertTriangle} accent="red" />
        <KpiCard label="High-risk areas" value={kpis.highPlus} icon={TrendingUp} accent="amber" />
        <KpiCard label="Clusters monitored" value={kpis.clusters} icon={Layers} accent="blue" />
        <KpiCard
          label="Top shortage"
          value={kpis.top ? kpis.top.cluster : '-'}
          hint={kpis.top ? kpis.top.machine_type : ''}
          icon={Activity}
          accent="emerald"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          <Segmented options={FILTERS} value={filter} onChange={setFilter} />
          <Card title="Predicted demand by cluster & machine type" subtitle="Click a row to see the reasoning">
            {rows.length === 0 ? (
              <EmptyState
                title="No demand in this view"
                description="Try a different filter, or run the seed script to populate the demo dataset."
              />
            ) : (
              <Table
                columns={COLUMNS}
                rows={rows}
                renderCell={renderCell}
                onRowClick={(row) => setSelectedId(row.id)}
                activeId={selectedId}
              />
            )}
          </Card>
        </div>

        <div>
          {selected ? (
            <DetailPanel
              insight={selected}
              onFindMachine={() =>
                navigate(
                  `/allocation?cluster=${encodeURIComponent(selected.cluster)}` +
                    `&type=${encodeURIComponent(selected.machine_type)}`,
                )
              }
            />
          ) : (
            <Card title="Why this matters">
              <EmptyState title="Select a row" description="Pick a cluster to see its factor breakdown." />
            </Card>
          )}
        </div>
      </div>
    </PageShell>
  )
}

function PageShell({ children }) {
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Demand Intelligence</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Where machinery demand is set to outstrip supply over the next few days, and why.
        </p>
      </header>
      {children}
    </div>
  )
}

function Segmented({ options, value, onChange }) {
  return (
    <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
      {options.map((o) => (
        <button
          key={o.key}
          onClick={() => onChange(o.key)}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            value === o.key ? 'bg-emerald-600 text-white' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-lg font-semibold text-slate-900">{value}</div>
    </div>
  )
}

function DetailPanel({ insight, onFindMachine }) {
  const f = insight.factors || {}
  const w = f.weights || {}
  const factorList = [
    { label: 'Historical demand', value: f.historical_score, weight: w.historical },
    { label: 'Crop calendar', value: f.crop_calendar_score, weight: w.crop_calendar },
    { label: 'Live requests', value: f.live_request_score, weight: w.live_request },
    { label: 'Request momentum', value: f.momentum_score, weight: w.momentum },
  ]
  const pct = Math.round((insight.shortage_probability ?? 0) * 100)
  const barColor = pct >= 75 ? 'bg-red-500' : pct >= 50 ? 'bg-orange-500' : pct >= 25 ? 'bg-amber-500' : 'bg-emerald-500'

  return (
    <Card title="Why this matters" subtitle={`${insight.cluster} · ${insight.machine_type}`}>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <RiskPill level={insight.risk_level} />
          <span className="text-sm text-slate-500">demand score {insight.demand_score}/100</span>
        </div>

        <p className="text-sm text-slate-600">{insight.reason}</p>

        <div>
          <div className="flex justify-between text-xs text-slate-500">
            <span>Shortage probability</span>
            <span className="tabular-nums">{pct}%</span>
          </div>
          <div className="mt-1 h-2 rounded bg-slate-100">
            <div className={`h-2 rounded ${barColor}`} style={{ width: `${pct}%` }} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <MiniStat label="Expected requests" value={insight.expected_requests} />
          <MiniStat label="Available machines" value={insight.available_supply} />
        </div>

        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            Score factors
          </div>
          <FactorBars factors={factorList} />
        </div>

        <Button className="w-full" onClick={onFindMachine}>
          <Search size={16} />
          Find a machine
        </Button>
      </div>
    </Card>
  )
}

function LoadingView() {
  return (
    <PageShell>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <SkeletonCard />
        </div>
        <SkeletonCard />
      </div>
    </PageShell>
  )
}
