import { useMemo } from 'react'

import Card from '../components/ui/Card'
import KpiCard from '../components/ui/KpiCard'
import EmptyState from '../components/states/EmptyState'
import ErrorState from '../components/states/ErrorState'
import MapView from '../components/map/MapView'
import { useMapMachines, useMapShortages } from '../hooks/useMapData'
import { useChcs } from '../hooks/useNetwork'
import { useRelocations } from '../hooks/useRelocations'

const LEGEND = [
  { label: 'Available', dot: 'bg-emerald-500' },
  { label: 'Booked', dot: 'bg-amber-500' },
  { label: 'In transit', dot: 'bg-blue-500' },
  { label: 'Maintenance', dot: 'bg-slate-400' },
  { label: 'CHC', dot: 'bg-teal-700' },
  { label: 'Shortage zone', dot: 'bg-red-400' },
  { label: 'Relocation move', line: true },
]

export default function MapPage() {
  const chcsQ = useChcs()
  const machinesQ = useMapMachines()
  const shortagesQ = useMapShortages()
  const relocationsQ = useRelocations()

  const chcs = chcsQ.data ?? []
  const machines = machinesQ.data ?? []
  const shortages = shortagesQ.data ?? []
  const relocations = relocationsQ.data ?? []

  const counts = useMemo(() => {
    const c = { available: 0, booked: 0, in_transit: 0, maintenance: 0 }
    machines.forEach((m) => {
      c[m.status] = (c[m.status] || 0) + 1
    })
    return c
  }, [machines])

  // Turn approved relocations into dashed lines: source CHC coordinates ->
  // destination cluster centroid (from the shortage data). Generic: any approved
  // move whose source CHC and destination cluster are known gets a line. We never
  // fabricate coordinates - if either endpoint is unknown, we simply skip it.
  const relocationLines = useMemo(() => {
    const chcById = new Map(chcs.map((c) => [c.id, c]))
    const centroidByCluster = new Map(shortages.map((s) => [s.cluster, s]))
    return relocations
      .filter((r) => r.status === 'approved')
      .map((r) => {
        const src = chcById.get(r.from_chc_id)
        const dst = centroidByCluster.get(r.to_cluster)
        if (!src || !dst) return null
        return {
          id: r.id,
          machineId: r.machine_id,
          machineType: r.machine_type,
          fromName: r.from_chc_name,
          toCluster: r.to_cluster,
          from: [src.latitude, src.longitude],
          to: [dst.latitude, dst.longitude],
        }
      })
      .filter(Boolean)
  }, [relocations, chcs, shortages])

  // Relocation data is non-essential to the map, so a failure there shouldn't
  // block rendering - only the core layers gate loading/error.
  const loading = chcsQ.isLoading || machinesQ.isLoading || shortagesQ.isLoading
  const error = chcsQ.error || machinesQ.error || shortagesQ.error
  const isEmpty =
    !loading && !error && chcs.length === 0 && machines.length === 0 && shortages.length === 0

  const refetchAll = () => {
    chcsQ.refetch()
    machinesQ.refetch()
    shortagesQ.refetch()
    relocationsQ.refetch()
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Live Map</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          The network at a glance: centres, machines by status, shortage zones and moves in progress.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-4">
        <KpiCard label="Available" value={counts.available} accent="emerald" />
        <KpiCard label="Booked" value={counts.booked} accent="amber" />
        <KpiCard label="In transit" value={counts.in_transit} accent="blue" />
        <KpiCard label="Shortage zones" value={shortages.length} accent="red" />
      </div>

      <Card>
        {error ? (
          <ErrorState message={error?.message || 'Failed to load map data.'} onRetry={refetchAll} />
        ) : loading ? (
          <div className="h-[520px] w-full animate-pulse rounded-xl bg-slate-100" />
        ) : isEmpty ? (
          <EmptyState
            title="Nothing to map yet"
            description="No centres, machines or shortage zones are available to display."
          />
        ) : (
          <>
            <MapView
              chcs={chcs}
              machines={machines}
              shortages={shortages}
              relocations={relocationLines}
            />
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
              {LEGEND.map((l) => (
                <span key={l.label} className="flex items-center gap-1.5 text-xs text-slate-600">
                  {l.line ? (
                    <span className="h-0 w-5 border-t-2 border-dashed border-blue-500" />
                  ) : (
                    <span className={`h-2.5 w-2.5 rounded-full ${l.dot}`} />
                  )}
                  {l.label}
                </span>
              ))}
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
