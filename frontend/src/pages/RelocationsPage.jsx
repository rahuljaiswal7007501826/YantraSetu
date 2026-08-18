import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, CheckCircle2, Coins, Plus, Shuffle } from 'lucide-react'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import KpiCard from '../components/ui/KpiCard'
import StatusBadge from '../components/ui/StatusBadge'
import Table from '../components/ui/Table'
import NetBenefitBreakdown from '../components/explain/NetBenefitBreakdown'
import EmptyState from '../components/states/EmptyState'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import { useRole } from '../context/RoleContext'
import { useRelocationActions, useRelocations } from '../hooks/useRelocations'

const rupees = (n) => `Rs ${Math.round(n ?? 0).toLocaleString('en-IN')}`

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
]

const COLUMNS = [
  { key: 'machine', label: 'Machine' },
  { key: 'move', label: 'Move' },
  { key: 'net_benefit', label: 'Net benefit', align: 'right' },
  { key: 'status', label: 'Status' },
]

export default function RelocationsPage() {
  const { role } = useRole()
  const canAct = role === 'chc_operator'
  const { data, isLoading, isError, error, refetch } = useRelocations()
  const { approve, reject, generate } = useRelocationActions()

  const recs = data ?? []
  const [filter, setFilter] = useState('all')
  const [selectedId, setSelectedId] = useState(null)

  const kpis = useMemo(() => {
    const pending = recs.filter((r) => r.status === 'pending')
    return {
      pending: pending.length,
      approved: recs.filter((r) => r.status === 'approved').length,
      potential: pending.reduce((s, r) => s + (r.net_benefit || 0), 0),
    }
  }, [recs])

  const rows = useMemo(() => {
    const filtered = filter === 'all' ? recs : recs.filter((r) => r.status === filter)
    return filtered.map((r) => ({ ...r, id: r.id }))
  }, [recs, filter])

  useEffect(() => {
    if (rows.length && !rows.some((r) => r.id === selectedId)) setSelectedId(rows[0].id)
  }, [rows, selectedId])
  const selected = rows.find((r) => r.id === selectedId) || rows[0] || null

  if (isLoading) {
    return (
      <Shell>
        <div className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <SkeletonCard />
      </Shell>
    )
  }
  if (isError) {
    return (
      <Shell>
        <ErrorState message={error?.message || 'Failed to load recommendations.'} onRetry={refetch} />
      </Shell>
    )
  }

  const renderCell = (row, col) => {
    if (col.key === 'machine') return `#${row.machine_id} · ${row.machine_type}`
    if (col.key === 'move') return `${row.from_chc_name} -> ${row.to_cluster}`
    if (col.key === 'net_benefit') return rupees(row.net_benefit)
    if (col.key === 'status') return <StatusBadge status={row.status} />
    return row[col.key]
  }

  const generateBtn = canAct && (
    <Button variant="secondary" onClick={() => generate.mutate()} disabled={generate.isPending}>
      <Plus size={16} />
      {generate.isPending ? 'Generating...' : 'Generate'}
    </Button>
  )

  return (
    <Shell>
      <div className="grid gap-4 sm:grid-cols-3">
        <KpiCard label="Pending approvals" value={kpis.pending} icon={Shuffle} accent="amber" />
        <KpiCard label="Approved" value={kpis.approved} icon={CheckCircle2} accent="emerald" />
        <KpiCard label="Potential net benefit" value={rupees(kpis.potential)} icon={Coins} accent="blue" hint="from pending moves" />
      </div>

      <div className="flex items-center justify-between gap-3">
        <Segmented options={FILTERS} value={filter} onChange={setFilter} />
        {generateBtn}
      </div>

      {recs.length === 0 ? (
        <Card>
          <EmptyState
            title="No relocation recommendations"
            description={canAct ? 'Generate recommendations to see cross-CHC moves the engine suggests.' : 'None yet. An operator can generate them.'}
            action={
              canAct ? (
                <Button onClick={() => generate.mutate()} disabled={generate.isPending}>
                  <Plus size={16} />
                  {generate.isPending ? 'Generating...' : 'Generate recommendations'}
                </Button>
              ) : null
            }
          />
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Card title="Cross-CHC relocation recommendations" subtitle="Click a row to review the money case">
              <Table
                columns={COLUMNS}
                rows={rows}
                renderCell={renderCell}
                onRowClick={(row) => setSelectedId(row.id)}
                activeId={selectedId}
                emptyLabel="No recommendations in this view"
              />
            </Card>
          </div>
          <div>
            {selected && (
              <RelocationDetail rec={selected} canAct={canAct} approve={approve} reject={reject} />
            )}
          </div>
        </div>
      )}
    </Shell>
  )
}

function Shell({ children }) {
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Relocation Recommendations</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Cross-CHC moves the engine recommends, justified by net benefit. Nothing moves without approval.
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
      <div className="mt-0.5 text-sm font-semibold text-slate-900">{value}</div>
    </div>
  )
}

function RelocationDetail({ rec, canAct, approve, reject }) {
  const isPending = rec.status === 'pending'
  const actionError = approve.error || reject.error
  const busy = approve.isPending || reject.isPending

  return (
    <Card title="Recommended move" subtitle={`#${rec.machine_id} · ${rec.machine_type}`}>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <StatusBadge status={rec.status} />
        </div>

        <div className="flex items-center gap-2 text-sm text-slate-700">
          <span className="rounded-md bg-slate-100 px-2 py-1">{rec.from_chc_name}</span>
          <ArrowRight size={16} className="text-slate-400" />
          <span className="rounded-md bg-emerald-100 px-2 py-1 text-emerald-800">{rec.to_cluster}</span>
        </div>

        <p className="text-sm text-slate-600">{rec.explanation}</p>

        <div className="grid grid-cols-2 gap-3">
          <MiniStat label="Farmers served" value={rec.expected_farmers_served} />
          <MiniStat label="Relocation cost" value={rupees(rec.relocation_cost)} />
        </div>

        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            Net benefit breakdown
          </div>
          <NetBenefitBreakdown breakdown={rec.benefit_breakdown} netBenefit={rec.net_benefit} />
        </div>

        {isPending ? (
          canAct ? (
            <div className="space-y-2">
              <div className="flex gap-2">
                <Button className="flex-1" onClick={() => approve.mutate(rec.id)} disabled={busy}>
                  {approve.isPending ? 'Approving...' : 'Approve'}
                </Button>
                <Button variant="danger" className="flex-1" onClick={() => reject.mutate(rec.id)} disabled={busy}>
                  {reject.isPending ? 'Rejecting...' : 'Reject'}
                </Button>
              </div>
              {actionError && <p className="text-xs text-red-600">{actionError.message}</p>}
            </div>
          ) : (
            <p className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
              Approval is a CHC Operator action. Switch role (top-right) to approve or reject.
            </p>
          )
        ) : (
          <p className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
            Status: <span className="font-medium capitalize">{rec.status}</span>.
            {rec.status === 'approved' && ' The machine is now in transit (not auto-completed).'}
          </p>
        )}
      </div>
    </Card>
  )
}
