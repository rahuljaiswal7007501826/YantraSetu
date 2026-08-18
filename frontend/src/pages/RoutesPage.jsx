import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MapPin, Route as RouteIcon } from 'lucide-react'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import ErrorState from '../components/states/ErrorState'
import MapView from '../components/map/MapView'
import { useMachines } from '../hooks/useNetwork'
import { useOptimizeRoute } from '../hooks/useRoutes'
import { useRequests } from '../hooks/useRequests'

const fmtDuration = (min) => {
  const h = Math.floor((min || 0) / 60)
  const m = (min || 0) % 60
  return h ? `${h}h ${m}m` : `${m}m`
}

export default function RoutesPage() {
  const [params] = useSearchParams()
  const machineParam = params.get('machine')

  const machinesQ = useMachines()
  const requestsQ = useRequests({ status: 'pending', limit: 20 })
  const optimize = useOptimizeRoute()

  const machines = machinesQ.data ?? []
  const requests = requestsQ.data ?? []

  // request id -> full request (has farmer_name, crop_type) for stop popups/labels.
  const requestsById = useMemo(
    () => Object.fromEntries(requests.map((r) => [r.id, r])),
    [requests],
  )

  const [machineId, setMachineId] = useState(null)
  const [selectedReqs, setSelectedReqs] = useState([])

  useEffect(() => {
    if (!machineId && machines.length) {
      const preset = machineParam ? Number(machineParam) : null
      const combine = machines.find((m) => m.machine_type === 'Combine Harvester')
      setMachineId(preset || combine?.id || machines[0].id)
    }
  }, [machines, machineId, machineParam])

  useEffect(() => {
    if (!selectedReqs.length && requests.length) {
      setSelectedReqs(requests.slice(0, 4).map((r) => r.id))
    }
  }, [requests, selectedReqs])

  const toggleReq = (id) =>
    setSelectedReqs((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))

  const runOptimize = () => {
    if (machineId && selectedReqs.length) {
      optimize.mutate({ machine_id: machineId, request_ids: selectedReqs })
    }
  }

  const result = optimize.data

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Route Optimization</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Sequence a machine&apos;s farmer visits into an efficient day plan (OR-Tools VRP with time windows).
        </p>
      </header>

      <Card title="Plan a route">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Machine</label>
            <select
              value={machineId ?? ''}
              onChange={(e) => setMachineId(Number(e.target.value))}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none"
            >
              {machines.map((m) => (
                <option key={m.id} value={m.id}>
                  {`#${m.id} · ${m.machine_type}`}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <Button onClick={runOptimize} disabled={!machineId || selectedReqs.length === 0 || optimize.isPending}>
              <RouteIcon size={16} />
              {optimize.isPending ? 'Optimizing...' : `Optimize (${selectedReqs.length} stops)`}
            </Button>
          </div>
        </div>

        <div className="mt-4">
          <div className="mb-1 text-xs font-medium text-slate-500">Farmer stops (pending requests)</div>
          <div className="max-h-52 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2">
            {requests.map((r) => (
              <label key={r.id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-slate-50">
                <input type="checkbox" checked={selectedReqs.includes(r.id)} onChange={() => toggleReq(r.id)} />
                <span className="text-slate-700">
                  #{r.id} · {r.farmer_name} · {r.crop_type} · {r.operation_type}
                </span>
              </label>
            ))}
            {requests.length === 0 && <div className="px-2 py-3 text-sm text-slate-400">No pending requests.</div>}
          </div>
        </div>
      </Card>

      {optimize.isError && (
        <ErrorState message={optimize.error?.message || 'Route optimization failed.'} onRetry={runOptimize} />
      )}

      {result && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Day plan" subtitle={`${result.total_distance_km} km · ${fmtDuration(result.total_route_duration_min)} · ${result.total_travel_time_min}m driving`}>
            <ol className="space-y-3">
              {result.stops.map((s) => (
                <li key={s.sequence_number} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <span className={`grid h-6 w-6 place-items-center rounded-full text-xs font-semibold ${s.is_depot ? 'bg-teal-700 text-white' : 'bg-blue-600 text-white'}`}>
                      {s.is_depot ? 'D' : s.sequence_number}
                    </span>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-slate-800">
                      {s.is_depot
                        ? 'Depot (start)'
                        : requestsById[s.request_id]?.farmer_name
                          ? `${requestsById[s.request_id].farmer_name} · Req #${s.request_id}`
                          : `Farmer request #${s.request_id}`}
                    </div>
                    <div className="text-xs text-slate-500">
                      arrive {s.arrival_clock}
                      {!s.is_depot && ` · service ${s.service_start_clock} (${s.service_duration_min}m)`}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
            {result.dropped_stop_ids?.length > 0 && (
              <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                Dropped (couldn&apos;t fit time windows): {result.dropped_stop_ids.join(', ')}
              </div>
            )}
            <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
              <MapPin size={13} />
              Returns to depot: {result.returned_to_depot ? 'yes' : 'no'} · <StatusBadge status={result.status?.toLowerCase?.() || 'optimized'} />
            </div>
          </Card>

          <Card title="Route map">
            <MapView route={result} requestsById={requestsById} height="h-[440px]" />
          </Card>
        </div>
      )}
    </div>
  )
}
