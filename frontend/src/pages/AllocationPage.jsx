import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, Coins, MapPin, Truck, Users } from 'lucide-react'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import Table from '../components/ui/Table'
import FactorBars from '../components/explain/FactorBars'
import EmptyState from '../components/states/EmptyState'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import { useAllocation } from '../hooks/useAllocation'
import { useRequests } from '../hooks/useRequests'

const CANDIDATE_COLUMNS = [
  { key: 'rank', label: '#' },
  { key: 'machine', label: 'Machine' },
  { key: 'chc_name', label: 'CHC' },
  { key: 'score', label: 'Score', align: 'right' },
  { key: 'distance_km', label: 'Dist (km)', align: 'right' },
  { key: 'relocation', label: 'Move?' },
]

export default function AllocationPage() {
  const [params] = useSearchParams()
  const cluster = params.get('cluster')
  const machineType = params.get('type')
  const navigate = useNavigate()

  const requestsQuery = useRequests({
    status: 'pending',
    ...(machineType ? { machine_type: machineType } : {}),
    limit: 50,
  })
  const requests = requestsQuery.data ?? []
  const [requestId, setRequestId] = useState(null)

  useEffect(() => {
    if (requests.length && !requests.some((r) => r.id === requestId)) {
      setRequestId(requests[0].id)
    }
  }, [requests, requestId])

  const allocationQuery = useAllocation(requestId)
  const result = allocationQuery.data
  const candidates = useMemo(() => result?.recommendations ?? [], [result])

  const [selectedMachineId, setSelectedMachineId] = useState(null)
  useEffect(() => {
    if (candidates.length && !candidates.some((c) => c.machine_id === selectedMachineId)) {
      setSelectedMachineId(candidates[0].machine_id)
    }
  }, [candidates, selectedMachineId])
  const selected = candidates.find((c) => c.machine_id === selectedMachineId) || candidates[0] || null

  const rows = candidates.map((c, i) => ({ ...c, id: c.machine_id, rank: i + 1 }))
  const renderCell = (row, col) => {
    if (col.key === 'machine') return `#${row.machine_id} · ${row.machine_type}`
    if (col.key === 'relocation')
      return row.relocation_required ? <StatusBadge status="in_transit" /> : <span className="text-slate-400">local</span>
    if (col.key === 'distance_km') return row.distance_km
    return row[col.key]
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Machine Allocation</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Ranked, compatible machines for a request, with the reasoning behind each score.
        </p>
      </header>

      {cluster && machineType && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm text-emerald-800">
          Addressing shortage: <strong>{cluster}</strong> · <strong>{machineType}</strong>
        </div>
      )}

      {/* Request picker */}
      <Card title="Choose a pending request to allocate">
        {requestsQuery.isLoading ? (
          <div className="h-10 animate-pulse rounded bg-slate-100" />
        ) : requestsQuery.isError ? (
          <ErrorState message={requestsQuery.error?.message} onRetry={requestsQuery.refetch} />
        ) : requests.length === 0 ? (
          <EmptyState
            title="No matching pending requests"
            description="There are no pending requests for this operation. Try the Demand screen or seed the dataset."
          />
        ) : (
          <select
            value={requestId ?? ''}
            onChange={(e) => setRequestId(Number(e.target.value))}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none"
          >
            {requests.map((r) => (
              <option key={r.id} value={r.id}>
                {`#${r.id} — ${r.farmer_name} · ${r.crop_type} · ${r.operation_type} (${r.urgency})`}
              </option>
            ))}
          </select>
        )}
      </Card>

      {/* Candidates */}
      {requestId && (
        <CandidatesSection
          query={allocationQuery}
          result={result}
          rows={rows}
          columns={CANDIDATE_COLUMNS}
          renderCell={renderCell}
          selectedMachineId={selectedMachineId}
          onSelect={setSelectedMachineId}
          selected={selected}
          onSeeRelocation={() => navigate('/relocations')}
        />
      )}
    </div>
  )
}

function CandidatesSection({
  query,
  result,
  rows,
  columns,
  renderCell,
  selectedMachineId,
  onSelect,
  selected,
  onSeeRelocation,
}) {
  if (query.isLoading) {
    return (
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <SkeletonCard />
        </div>
        <SkeletonCard />
      </div>
    )
  }
  if (query.isError) {
    return <ErrorState message={query.error?.message || 'Failed to compute recommendations.'} onRetry={query.refetch} />
  }
  if (!result || rows.length === 0) {
    return (
      <Card title="Ranked candidates">
        <EmptyState title="No compatible machine found" description={result?.message} />
      </Card>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <Card
          title="Ranked candidates"
          subtitle={`${result.candidate_count} compatible machine(s) · incompatible types excluded by the hard gate`}
        >
          <Table
            columns={columns}
            rows={rows}
            renderCell={renderCell}
            onRowClick={(row) => onSelect(row.machine_id)}
            activeId={selectedMachineId}
          />
        </Card>
      </div>
      <div>{selected && <CandidateDetail candidate={selected} onSeeRelocation={onSeeRelocation} />}</div>
    </div>
  )
}

function MiniStat({ icon: Icon, label, value }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center gap-1.5 text-xs text-slate-500">
        {Icon && <Icon size={13} />}
        {label}
      </div>
      <div className="mt-0.5 text-sm font-semibold text-slate-900">{value}</div>
    </div>
  )
}

function CandidateDetail({ candidate, onSeeRelocation }) {
  const fb = candidate.factor_breakdown || {}
  const w = fb.weights || {}
  const factors = [
    { label: 'Distance', value: fb.distance_score, weight: w.distance },
    { label: 'Urgency', value: fb.urgency_score, weight: w.urgency },
    { label: 'Compatibility', value: fb.compatibility_score, weight: w.compatibility },
    { label: 'Capacity fit', value: fb.capacity_fit, weight: w.capacity_fit },
    { label: 'Relocation cost', value: fb.relocation_cost_score, weight: w.relocation_cost },
    { label: 'Idle-capacity gain', value: fb.cluster_efficiency_gain, weight: w.cluster_efficiency_gain },
    { label: 'Future-demand avoidance', value: fb.future_demand_avoidance, weight: w.future_demand_avoidance },
  ]

  return (
    <Card title="Why this machine" subtitle={`#${candidate.machine_id} · ${candidate.machine_type}`}>
      <div className="space-y-4">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-semibold text-emerald-700">{candidate.score}</span>
          <span className="text-sm text-slate-500">/ 100 allocation score</span>
        </div>

        <p className="text-sm text-slate-600">{candidate.explanation}</p>

        <div className="grid grid-cols-2 gap-3">
          <MiniStat icon={MapPin} label="Distance" value={`${candidate.distance_km} km`} />
          <MiniStat icon={Coins} label="Relocation cost" value={`Rs ${candidate.estimated_relocation_cost}`} />
          <MiniStat icon={Users} label="Farmers served" value={candidate.expected_farmers_served} />
          <MiniStat
            icon={Truck}
            label="Relocation"
            value={candidate.relocation_required ? 'Required' : 'Local'}
          />
        </div>

        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
            Score factors
          </div>
          <FactorBars factors={factors} />
        </div>

        {candidate.relocation_required && (
          <Button className="w-full" onClick={onSeeRelocation}>
            See relocation recommendation
            <ArrowRight size={16} />
          </Button>
        )}
      </div>
    </Card>
  )
}
