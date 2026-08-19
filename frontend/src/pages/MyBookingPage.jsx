import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CalendarClock, MapPin, PlusCircle, Tractor } from 'lucide-react'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import SpeakButton from '../components/SpeakButton'
import StatusBadge from '../components/ui/StatusBadge'
import EmptyState from '../components/states/EmptyState'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import FarmerPicker from '../components/FarmerPicker'
import { hiStrings } from '../i18n/hi-strings'
import { useRole } from '../context/RoleContext'
import { useAllocation } from '../hooks/useAllocation'
import { useMyAssignment } from '../hooks/useMe'
import { useCancelRequest, useRequests } from '../hooks/useRequests'

const rupees = (n) => `Rs ${Math.round(n ?? 0).toLocaleString('en-IN')}`

export default function MyBookingPage() {
  const [farmerId, setFarmerId] = useState(null)

  // Seed to a farmer who has any request so the booking card has something to show.
  const seedQ = useRequests({ limit: 1 })
  useEffect(() => {
    if (farmerId == null && seedQ.data?.length) setFarmerId(seedQ.data[0].farmer_id)
  }, [seedQ.data, farmerId])

  const listParams = farmerId ? { farmer_id: farmerId, limit: 50 } : { limit: 1 }
  const reqsQ = useRequests(listParams)
  // Most recent request (the list is ordered by id ascending).
  const current = farmerId && reqsQ.data?.length ? reqsQ.data[reqsQ.data.length - 1] : null

  const cancel = useCancelRequest()
  const canCancel = current && ['pending', 'allocated', 'scheduled'].includes(current.status)

  // Farmer: read-only assignment via the self-service endpoint (the staff
  // allocation endpoint is never exposed to farmers). Staff: the allocation view.
  const { role } = useRole()
  const isFarmer = role === 'farmer'
  const allocQ = useAllocation(isFarmer ? null : current?.id)
  const assignQ = useMyAssignment(isFarmer ? current?.id : null)
  const activeQ = isFarmer ? assignQ : allocQ
  const machine = isFarmer ? assignQ.data?.assigned_machine : allocQ.data?.recommendations?.[0]

  // Spoken audio matches the on-screen assignment state (confirmed vs preview vs
  // none). English text is for the accessible label; Hindi is what's read aloud.
  const isConfirmed = ['allocated', 'scheduled'].includes(current?.status)
  const speakEnglish = !machine
    ? 'No machine is available for your request yet. The network is looking for one.'
    : isConfirmed
      ? `${machine.chc_name} confirmed the ${machine.machine_type} for your request.`
      : `The network recommends the ${machine.machine_type} from ${machine.chc_name} for your request.`
  const speakHindi = !machine
    ? hiStrings.noMachineYet
    : isConfirmed
      ? hiStrings.assignmentConfirmed({ machineType: machine.machine_type, chcName: machine.chc_name })
      : hiStrings.assignmentPreview({ machineType: machine.machine_type, chcName: machine.chc_name })

  const busy = farmerId == null || reqsQ.isLoading

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">My Booking</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Your latest request and its assigned machine.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <FarmerPicker value={farmerId} onChange={setFarmerId} />
          {canCancel && (
            <Button
              variant="danger"
              onClick={() => cancel.mutate(current.id)}
              disabled={cancel.isPending}
            >
              {cancel.isPending ? 'Cancelling...' : 'Cancel request'}
            </Button>
          )}
        </div>
      </header>

      {reqsQ.isError ? (
        <ErrorState message={reqsQ.error?.message || 'Failed to load your booking.'} onRetry={reqsQ.refetch} />
      ) : busy ? (
        <SkeletonCard />
      ) : !current ? (
        <Card>
          <EmptyState
            title="No active request"
            description="You have no pending request. Create one to get a machine assigned."
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
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Your request" subtitle={`Request #${current.id}`}>
            <dl className="space-y-2.5 text-sm">
              <Field label="Status" value={<StatusBadge status={current.status} />} />
              <Field label="Operation" value={current.operation_type} />
              <Field label="Crop" value={current.crop_type} />
              <Field label="Preferred date" value={current.requested_date} />
              <Field
                label="Field"
                value={
                  <span className="inline-flex items-center gap-1">
                    <MapPin size={14} className="text-slate-400" />
                    {current.village}
                  </span>
                }
              />
            </dl>
            <Link
              to={`/request/${current.id}`}
              className="mt-4 inline-block text-sm font-medium text-emerald-700 hover:underline"
            >
              View full request &rarr;
            </Link>
          </Card>

          <Card
            title="Assigned machine"
            subtitle={
              ['allocated', 'scheduled'].includes(current.status)
                ? 'Confirmed by your CHC'
                : 'Preview from the allocation engine'
            }
          >
            {activeQ.isLoading ? (
              <SkeletonCard />
            ) : activeQ.isError ? (
              <ErrorState
                message={activeQ.error?.message || 'Could not compute your assignment.'}
                onRetry={activeQ.refetch}
              />
            ) : !machine ? (
              <p className="text-sm text-slate-600">
                No machine is available for your request yet. The network is looking for one.
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
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <MiniStat label="Distance to field" value={`${machine.distance_km} km`} />
                  <MiniStat label="Compatible" value={machine.compatible ? 'Yes' : 'No'} />
                </div>

                <p className="flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
                  <CalendarClock size={14} className="mt-0.5 shrink-0 text-slate-400" />
                  This is the machine the network recommends for your request. Your CHC confirms the
                  exact time slot once the schedule is finalised.
                </p>
              </div>
            )}
            {!activeQ.isLoading && !activeQ.isError && (
              <div className="mt-3 flex justify-end">
                <SpeakButton text={speakEnglish} hindi={speakHindi} />
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
