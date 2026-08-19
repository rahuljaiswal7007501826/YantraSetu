import { useState } from 'react'
import { Sparkles, Tractor, X } from 'lucide-react'

import { useAllocation } from '../hooks/useAllocation'
import { useMachines } from '../hooks/useNetwork'
import { useAssignRequest, useRejectRequest } from '../hooks/useRequests'
import Button from './ui/Button'

/**
 * Assign (directly or via ranked recommendations) or reject a pending request.
 * Rendered as a lightweight modal; closes itself on a successful action.
 */
export default function AssignMachineModal({ request, onClose }) {
  const [tab, setTab] = useState('recommend') // 'recommend' | 'direct' | 'reject'
  const assign = useAssignRequest()
  const reject = useRejectRequest()
  const err = assign.error?.message || reject.error?.message

  const done = () => onClose?.()

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" onMouseDown={onClose}>
      <div
        className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-slate-100 px-5 py-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Request #{request.id} · {request.operation_type}
            </h3>
            <p className="text-xs text-slate-500">
              {request.farmer_name} · {request.village} · {request.crop_type}
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-slate-400 hover:bg-slate-100" aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div className="flex gap-1 border-b border-slate-100 px-3 pt-2">
          {[
            ['recommend', 'Ranked recommendations'],
            ['direct', 'Pick directly'],
            ['reject', 'Reject'],
          ].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`rounded-t-lg px-3 py-1.5 text-xs font-medium ${
                tab === key ? 'bg-slate-100 text-slate-900' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="max-h-[60vh] overflow-y-auto p-5">
          {err && (
            <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {err}
            </div>
          )}
          {tab === 'recommend' && (
            <RecommendTab request={request} assign={assign} onDone={done} />
          )}
          {tab === 'direct' && <DirectTab request={request} assign={assign} onDone={done} />}
          {tab === 'reject' && <RejectTab request={request} reject={reject} onDone={done} />}
        </div>
      </div>
    </div>
  )
}

function RecommendTab({ request, assign, onDone }) {
  const { data, isLoading, isError, error } = useAllocation(request.id, 5)
  const recs = data?.recommendations ?? []

  const assignId = (machineId) =>
    assign.mutate({ id: request.id, machineId }, { onSuccess: onDone })
  const assignTop = () =>
    assign.mutate({ id: request.id, useRecommendation: true }, { onSuccess: onDone })

  if (isLoading) return <p className="text-sm text-slate-400">Ranking machines...</p>
  if (isError) return <p className="text-sm text-red-500">{error?.message || 'Could not load recommendations.'}</p>
  if (recs.length === 0) {
    return (
      <p className="text-sm text-slate-600">
        {data?.message || 'No compatible, available machine was found. Consider rejecting the request.'}
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <Button onClick={assignTop} disabled={assign.isPending} className="w-full">
        <Sparkles size={16} /> Assign top pick (#{recs[0].machine_id} · {recs[0].machine_type})
      </Button>
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">Or choose one</div>
      <ul className="space-y-2">
        {recs.map((r) => (
          <li key={r.machine_id} className="flex items-center gap-3 rounded-lg border border-slate-200 p-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-emerald-50 text-emerald-700">
              <Tractor size={16} />
            </span>
            <div className="flex-1">
              <div className="text-sm font-medium text-slate-800">
                #{r.machine_id} · {r.machine_type}
              </div>
              <div className="text-xs text-slate-500">
                {r.chc_name} · {r.distance_km} km · score {Math.round(r.score)}
              </div>
            </div>
            <Button variant="secondary" onClick={() => assignId(r.machine_id)} disabled={assign.isPending}>
              Assign
            </Button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function DirectTab({ request, assign, onDone }) {
  const { data: machines = [], isLoading } = useMachines()
  const [machineId, setMachineId] = useState('')

  const submit = () =>
    assign.mutate({ id: request.id, machineId: Number(machineId) }, { onSuccess: onDone })

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">
        Pick any machine. The server rejects a machine whose type cannot perform this operation.
      </p>
      <select
        value={machineId}
        onChange={(e) => setMachineId(e.target.value)}
        disabled={isLoading}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
      >
        <option value="">{isLoading ? 'Loading machines...' : 'Select a machine'}</option>
        {machines.map((m) => (
          <option key={m.id} value={m.id}>
            #{m.id} · {m.machine_type}
          </option>
        ))}
      </select>
      <Button onClick={submit} disabled={!machineId || assign.isPending} className="w-full">
        {assign.isPending ? 'Assigning...' : 'Assign machine'}
      </Button>
    </div>
  )
}

function RejectTab({ request, reject, onDone }) {
  const [reason, setReason] = useState('')
  const submit = () =>
    reject.mutate({ id: request.id, reason: reason.trim() }, { onSuccess: onDone })

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">
        Reject when no suitable machine exists. The farmer is notified with your reason.
      </p>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        rows={3}
        placeholder="Reason (required), e.g. no combine harvester available this week"
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
      />
      <Button variant="danger" onClick={submit} disabled={!reason.trim() || reject.isPending} className="w-full">
        {reject.isPending ? 'Rejecting...' : 'Reject request'}
      </Button>
    </div>
  )
}
