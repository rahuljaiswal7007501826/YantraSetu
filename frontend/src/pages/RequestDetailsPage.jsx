import { Link, useLocation, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, MapPin, Tractor } from 'lucide-react'

import Card from '../components/ui/Card'
import SpeakButton from '../components/SpeakButton'
import StatusBadge from '../components/ui/StatusBadge'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import { hiStrings } from '../i18n/hi-strings'
import { useAllocation } from '../hooks/useAllocation'
import { useRequest } from '../hooks/useRequests'

const REQUEST_REGISTERED_EN = 'Your request has been registered successfully.'

const rupees = (n) => `Rs ${Math.round(n ?? 0).toLocaleString('en-IN')}`

export default function RequestDetailsPage() {
  const { id } = useParams()
  const reqId = Number(id)
  const location = useLocation()
  const justCreated = Boolean(location.state?.justCreated)
  const { data: req, isLoading, isError, error, refetch } = useRequest(reqId)

  // Only ask the allocation engine for a machine while the request is still pending.
  const allocQ = useAllocation(req?.status === 'pending' ? reqId : null)
  const machine = allocQ.data?.recommendations?.[0]

  return (
    <div className="space-y-5">
      <header>
        <Link to="/my-requests" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
          <ArrowLeft size={15} /> Back to my requests
        </Link>
        <h1 className="mt-1 text-xl font-semibold text-slate-900">Request #{reqId}</h1>
      </header>

      {justCreated && (
        <div className="flex items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
          <p className="inline-flex items-center gap-2 text-sm font-medium text-emerald-800">
            <CheckCircle2 size={18} className="shrink-0 text-emerald-600" />
            {REQUEST_REGISTERED_EN}
          </p>
          <SpeakButton text={REQUEST_REGISTERED_EN} hindi={hiStrings.requestRegistered} />
        </div>
      )}

      {isError ? (
        <ErrorState message={error?.message || 'Failed to load the request.'} onRetry={refetch} />
      ) : isLoading || !req ? (
        <SkeletonCard />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Request details">
            <dl className="space-y-2.5 text-sm">
              <Field label="Status" value={<StatusBadge status={req.status} />} />
              <Field label="Operation" value={req.operation_type} />
              <Field label="Crop" value={req.crop_type} />
              <Field label="Urgency" value={<span className="capitalize">{req.urgency}</span>} />
              <Field label="Preferred date" value={req.requested_date} />
              <Field label="Farmer" value={`${req.farmer_name} (#${req.farmer_id})`} />
              <Field
                label="Location"
                value={
                  <span className="inline-flex items-center gap-1">
                    <MapPin size={14} className="text-slate-400" />
                    {req.village} · {req.latitude.toFixed(3)}, {req.longitude.toFixed(3)}
                  </span>
                }
              />
            </dl>
          </Card>

          <Card title="Assigned machine" subtitle="Best match from the allocation engine">
            {req.status !== 'pending' ? (
              <p className="text-sm text-slate-600">
                This request is <span className="font-medium capitalize">{req.status}</span>. A live
                recommendation is shown only while a request is pending.
              </p>
            ) : allocQ.isLoading ? (
              <SkeletonCard />
            ) : allocQ.isError ? (
              <ErrorState
                message={allocQ.error?.message || 'Could not compute a recommendation.'}
                onRetry={allocQ.refetch}
              />
            ) : !machine ? (
              <p className="text-sm text-slate-600">
                No suitable machine is available for this request right now.
              </p>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-lg bg-emerald-50 text-emerald-700">
                    <Tractor size={18} />
                  </span>
                  <div>
                    <div className="text-sm font-semibold text-slate-900">
                      #{machine.machine_id} · {machine.machine_type}
                    </div>
                    <div className="text-xs text-slate-500">{machine.chc_name}</div>
                  </div>
                  <div className="ml-auto text-right">
                    <div className="text-lg font-semibold text-emerald-700">{machine.score}</div>
                    <div className="text-xs text-slate-400">score / 100</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <MiniStat label="Distance" value={`${machine.distance_km} km`} />
                  <MiniStat label="Farmers served" value={machine.expected_farmers_served} />
                  {machine.relocation_required && (
                    <MiniStat label="Relocation cost" value={rupees(machine.estimated_relocation_cost)} />
                  )}
                </div>

                <p className="text-sm text-slate-600">{machine.explanation}</p>

                {machine.relocation_required && (
                  <Link to="/relocations" className="text-sm font-medium text-emerald-700 hover:underline">
                    This needs a cross-CHC move &rarr; review relocation
                  </Link>
                )}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  )
}

function Field({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-800">{value}</dd>
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
