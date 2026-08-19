import { Link } from 'react-router-dom'
import { PlusCircle } from 'lucide-react'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import EmptyState from '../components/states/EmptyState'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import { useMyComplaints } from '../hooks/useComplaints'

const CATEGORY_LABELS = {
  machine_no_show: 'Machine did not show up',
  machine_breakdown: 'Machine breakdown',
  wrong_machine_type: 'Wrong machine type',
  operator_conduct: 'Operator conduct',
  chc_service: 'CHC service',
  other: 'Other',
}

const fmtDate = (s) => (s ? new Date(s).toLocaleDateString('en-IN') : '')

export default function FarmerMyComplaints() {
  const { data, isLoading, isError, error, refetch } = useMyComplaints()
  const complaints = data ?? []

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">My Complaints</h1>
          <p className="mt-0.5 text-sm text-slate-500">Your complaints and the staff responses.</p>
        </div>
        <Link to="/file-complaint">
          <Button>
            <PlusCircle size={16} /> File complaint
          </Button>
        </Link>
      </header>

      {isError ? (
        <ErrorState message={error?.message || 'Failed to load your complaints.'} onRetry={refetch} />
      ) : isLoading ? (
        <SkeletonCard />
      ) : complaints.length === 0 ? (
        <Card>
          <EmptyState
            title="No complaints"
            description="You haven't filed any complaints. If something went wrong, let us know."
            action={
              <Link to="/file-complaint">
                <Button>
                  <PlusCircle size={16} /> File complaint
                </Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {complaints.map((c) => (
            <Card key={c.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-slate-900">
                    {CATEGORY_LABELS[c.category] || c.category}
                  </div>
                  <div className="text-xs text-slate-400">
                    Complaint #{c.id} · {fmtDate(c.created_at)}
                    {c.demand_request_id ? ` · request #${c.demand_request_id}` : ''}
                  </div>
                </div>
                <StatusBadge status={c.status} />
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm text-slate-700">{c.description}</p>
              {c.staff_response && (
                <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50/60 p-3">
                  <div className="text-xs font-medium text-emerald-800">Staff response</div>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{c.staff_response}</p>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
