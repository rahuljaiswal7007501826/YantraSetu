import { useState } from 'react'
import { Clock } from 'lucide-react'

import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import Table from '../components/ui/Table'
import EmptyState from '../components/states/EmptyState'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import AssignMachineModal from '../components/AssignMachineModal'
import { useRequests } from '../hooks/useRequests'

const AGING_HOURS = 48

function ageInfo(createdAt) {
  const then = new Date(createdAt).getTime()
  if (Number.isNaN(then)) return { label: '', aging: false }
  const h = (Date.now() - then) / 3_600_000
  const label = h < 1 ? 'just now' : h < 24 ? `${Math.floor(h)}h ago` : `${Math.floor(h / 24)}d ago`
  return { label, aging: h >= AGING_HOURS }
}

const COLUMNS = [
  { key: 'id', label: 'Request' },
  { key: 'farmer_name', label: 'Farmer' },
  { key: 'village', label: 'Village' },
  { key: 'crop_type', label: 'Crop' },
  { key: 'operation_type', label: 'Operation' },
  { key: 'urgency', label: 'Urgency' },
  { key: 'age', label: 'Waiting' },
  { key: 'status', label: 'Status' },
]

export default function ManagerPendingRequests() {
  const [selected, setSelected] = useState(null)
  // Role-scoped: any manager/admin sees all pending requests (see docs/assumptions.md).
  const { data = [], isLoading, isError, error, refetch } = useRequests({
    status: 'pending',
    limit: 200,
  })

  const renderCell = (row, col) => {
    if (col.key === 'id') return `#${row.id}`
    if (col.key === 'status') return <StatusBadge status={row.status} />
    if (col.key === 'urgency') return <span className="capitalize">{row.urgency}</span>
    if (col.key === 'age') {
      const { label, aging } = ageInfo(row.created_at)
      return (
        <span
          className={`inline-flex items-center gap-1 ${aging ? 'font-medium text-red-600' : 'text-slate-500'}`}
          title={aging ? `Waiting over ${AGING_HOURS}h` : undefined}
        >
          <Clock size={13} />
          {label}
        </span>
      )
    }
    return row[col.key]
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Pending Requests</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Farmer requests awaiting a machine. Click a row to assign or reject.
        </p>
      </header>

      {isError ? (
        <ErrorState message={error?.message || 'Failed to load pending requests.'} onRetry={refetch} />
      ) : isLoading ? (
        <SkeletonCard />
      ) : data.length === 0 ? (
        <Card>
          <EmptyState
            title="Nothing pending"
            description="Every request has been handled. New requests will appear here."
          />
        </Card>
      ) : (
        <Card title="Awaiting assignment" subtitle={`${data.length} pending`}>
          <Table columns={COLUMNS} rows={data} renderCell={renderCell} onRowClick={setSelected} />
        </Card>
      )}

      {selected && <AssignMachineModal request={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
