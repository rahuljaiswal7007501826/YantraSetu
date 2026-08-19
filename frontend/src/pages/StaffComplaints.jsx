import { useState } from 'react'
import { Check, Lock, MessageSquare } from 'lucide-react'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import EmptyState from '../components/states/EmptyState'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import { useRole } from '../context/RoleContext'
import { useChcs } from '../hooks/useNetwork'
import {
  useAllComplaints,
  useChcComplaints,
  useCloseComplaint,
  useResolveComplaint,
  useRespondComplaint,
} from '../hooks/useComplaints'

const CATEGORY_LABELS = {
  machine_no_show: 'Machine did not show up',
  machine_breakdown: 'Machine breakdown',
  wrong_machine_type: 'Wrong machine type',
  operator_conduct: 'Operator conduct',
  chc_service: 'CHC service',
  other: 'Other',
}
const STATUSES = ['open', 'in_progress', 'resolved', 'closed']
const fmtDate = (s) => (s ? new Date(s).toLocaleDateString('en-IN') : '')
const selectCls =
  'rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 disabled:opacity-60'

export default function StaffComplaints() {
  const { role } = useRole()
  const isAdmin = role === 'district_admin'
  const chcsQ = useChcs()
  const chcs = chcsQ.data ?? []

  const [chcId, setChcId] = useState('') // '' = All CHCs (admin only)
  const [statusFilter, setStatusFilter] = useState('')

  const params = statusFilter ? { status: statusFilter } : {}
  // Admin with no CHC selected -> the all-complaints endpoint; otherwise the
  // CHC-scoped endpoint. Managers have no manager<->CHC link, so they must pick
  // a CHC to triage (the /admin endpoint is admin-only).
  const useAdminAll = isAdmin && !chcId
  const adminAllQ = useAllComplaints(params, { enabled: useAdminAll })
  const chcQ = useChcComplaints(chcId || null, params)
  const listQ = useAdminAll ? adminAllQ : chcQ
  const complaints = listQ.data ?? []

  const respond = useRespondComplaint()
  const resolve = useResolveComplaint()
  const close = useCloseComplaint()
  const busy = respond.isPending || resolve.isPending || close.isPending

  const needsChcPick = !isAdmin && !chcId

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Complaints</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          {isAdmin
            ? 'All farmer complaints across the network. Respond, resolve, and close.'
            : 'Pick a CHC to triage its complaints. Respond, resolve, and close.'}
        </p>
      </header>

      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <div className="grid gap-1">
            <label className="text-xs font-medium text-slate-500">CHC</label>
            <select value={chcId} onChange={(e) => setChcId(e.target.value)} className={selectCls}>
              <option value="">{isAdmin ? 'All CHCs' : 'Select a CHC...'}</option>
              {chcs.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-1">
            <label className="text-xs font-medium text-slate-500">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className={selectCls}
            >
              <option value="">All</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {needsChcPick ? (
        <Card>
          <EmptyState title="Pick a CHC" description="Select a CHC above to view its complaints." />
        </Card>
      ) : listQ.isError ? (
        <ErrorState message={listQ.error?.message || 'Failed to load complaints.'} onRetry={listQ.refetch} />
      ) : listQ.isLoading ? (
        <SkeletonCard />
      ) : complaints.length === 0 ? (
        <Card>
          <EmptyState title="No complaints" description="Nothing to triage here right now." />
        </Card>
      ) : (
        <div className="space-y-3">
          {complaints.map((c) => (
            <StaffComplaintCard
              key={c.id}
              complaint={c}
              categoryLabel={CATEGORY_LABELS[c.category] || c.category}
              busy={busy}
              onRespond={(text) => respond.mutate({ id: c.id, response: text })}
              onResolve={() => resolve.mutate(c.id)}
              onClose={() => close.mutate(c.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function StaffComplaintCard({ complaint: c, categoryLabel, busy, onRespond, onResolve, onClose }) {
  const [text, setText] = useState('')
  const canRespond = ['open', 'in_progress'].includes(c.status)
  const canClose = c.status === 'resolved'

  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-900">{categoryLabel}</div>
          <div className="text-xs text-slate-400">
            Complaint #{c.id} · farmer #{c.farmer_id} · {fmtDate(c.created_at)}
            {c.demand_request_id ? ` · request #${c.demand_request_id}` : ''}
            {c.machine_id ? ` · machine #${c.machine_id}` : ''}
          </div>
        </div>
        <StatusBadge status={c.status} />
      </div>
      <p className="mt-3 whitespace-pre-wrap text-sm text-slate-700">{c.description}</p>

      {c.staff_response && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div className="text-xs font-medium text-slate-600">Latest response</div>
          <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{c.staff_response}</p>
        </div>
      )}

      {canRespond && (
        <div className="mt-3 space-y-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={2}
            placeholder="Write a response to the farmer..."
            className={`w-full ${selectCls}`}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              disabled={!text.trim() || busy}
              onClick={() => {
                onRespond(text.trim())
                setText('')
              }}
            >
              <MessageSquare size={16} /> Send response
            </Button>
            <Button disabled={busy} onClick={onResolve}>
              <Check size={16} /> Resolve
            </Button>
          </div>
        </div>
      )}

      {canClose && (
        <div className="mt-3">
          <Button variant="secondary" disabled={busy} onClick={onClose}>
            <Lock size={16} /> Close
          </Button>
        </div>
      )}
    </Card>
  )
}
