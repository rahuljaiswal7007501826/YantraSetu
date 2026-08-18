import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PlusCircle } from 'lucide-react'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import Table from '../components/ui/Table'
import EmptyState from '../components/states/EmptyState'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import FarmerPicker from '../components/FarmerPicker'
import { useRequests } from '../hooks/useRequests'

const COLUMNS = [
  { key: 'id', label: 'Request' },
  { key: 'crop_type', label: 'Crop' },
  { key: 'operation_type', label: 'Operation' },
  { key: 'requested_date', label: 'Date' },
  { key: 'urgency', label: 'Urgency' },
  { key: 'status', label: 'Status' },
]

export default function MyRequestsPage() {
  const [farmerId, setFarmerId] = useState(null)
  const navigate = useNavigate()

  // Seed the picker to a farmer who actually has a request (a friendlier default
  // than farmer #1, who may have none).
  const seedQ = useRequests({ limit: 1 })
  useEffect(() => {
    if (farmerId == null && seedQ.data?.length) setFarmerId(seedQ.data[0].farmer_id)
  }, [seedQ.data, farmerId])

  const listParams = farmerId ? { farmer_id: farmerId, limit: 200 } : { limit: 1 }
  const { data, isLoading, isError, error, refetch } = useRequests(listParams)
  const busy = farmerId == null || isLoading

  const renderCell = (row, col) => {
    if (col.key === 'id') return `#${row.id}`
    if (col.key === 'status') return <StatusBadge status={row.status} />
    if (col.key === 'urgency') return <span className="capitalize">{row.urgency}</span>
    return row[col.key]
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">My Requests</h1>
          <p className="mt-0.5 text-sm text-slate-500">Your machinery requests and their status.</p>
        </div>
        <div className="flex items-center gap-3">
          <FarmerPicker value={farmerId} onChange={setFarmerId} />
          <Link to="/new-request">
            <Button>
              <PlusCircle size={16} /> New request
            </Button>
          </Link>
        </div>
      </header>

      {isError ? (
        <ErrorState message={error?.message || 'Failed to load requests.'} onRetry={refetch} />
      ) : busy ? (
        <SkeletonCard />
      ) : (data ?? []).length === 0 ? (
        <Card>
          <EmptyState
            title="No requests yet"
            description="Create a machinery request and it will show up here with its status."
            action={
              <Link to="/new-request">
                <Button>
                  <PlusCircle size={16} /> New request
                </Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <Card title="Your requests" subtitle="Click a request to see the assigned machine">
          <Table
            columns={COLUMNS}
            rows={data}
            renderCell={renderCell}
            onRowClick={(row) => navigate(`/request/${row.id}`)}
            emptyLabel="No requests"
          />
        </Card>
      )}
    </div>
  )
}
