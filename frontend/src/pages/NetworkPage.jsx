import { useMemo, useState } from 'react'
import { Building2, Tractor } from 'lucide-react'

import Card from '../components/ui/Card'
import KpiCard from '../components/ui/KpiCard'
import StatusBadge from '../components/ui/StatusBadge'
import Table from '../components/ui/Table'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import { useMapMachines } from '../hooks/useMapData'
import { useChcs } from '../hooks/useNetwork'

const COLUMNS = [
  { key: 'id', label: 'Machine' },
  { key: 'machine_type', label: 'Type' },
  { key: 'chc_name', label: 'CHC' },
  { key: 'status', label: 'Status' },
]

export default function NetworkPage() {
  const chcsQ = useChcs()
  const machinesQ = useMapMachines()
  const [selectedChc, setSelectedChc] = useState(null)

  const machines = machinesQ.data ?? []
  const chcs = chcsQ.data ?? []

  // Per-CHC totals so each centre card shows fleet size + how many are free.
  const byChc = useMemo(() => {
    const map = {}
    machines.forEach((m) => {
      const g = (map[m.chc_id] ||= { total: 0, available: 0 })
      g.total += 1
      if (m.status === 'available') g.available += 1
    })
    return map
  }, [machines])

  const rows = useMemo(
    () => (selectedChc ? machines.filter((m) => m.chc_id === selectedChc) : machines),
    [machines, selectedChc],
  )

  const loading = chcsQ.isLoading || machinesQ.isLoading
  const error = chcsQ.error || machinesQ.error

  const renderCell = (row, col) => {
    if (col.key === 'id') return `#${row.id}`
    if (col.key === 'status') return <StatusBadge status={row.status} />
    return row[col.key]
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">CHCs &amp; Machines</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          The fleet across every centre. Click a centre to filter its machines.
        </p>
      </header>

      {error ? (
        <ErrorState
          message={error?.message || 'Failed to load the network.'}
          onRetry={() => {
            chcsQ.refetch()
            machinesQ.refetch()
          }}
        />
      ) : loading ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-4">
            <KpiCard label="CHCs" value={chcs.length} icon={Building2} accent="slate" />
            <KpiCard label="Machines" value={machines.length} icon={Tractor} accent="emerald" />
            <KpiCard
              label="Available now"
              value={machines.filter((m) => m.status === 'available').length}
              accent="emerald"
            />
            <KpiCard
              label="In transit"
              value={machines.filter((m) => m.status === 'in_transit').length}
              accent="blue"
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ChcTile
              active={selectedChc === null}
              onClick={() => setSelectedChc(null)}
              name="All centres"
              sub={`${machines.length} machines`}
            />
            {chcs.map((c) => (
              <ChcTile
                key={c.id}
                active={selectedChc === c.id}
                onClick={() => setSelectedChc(c.id)}
                name={c.name}
                location={c.location}
                sub={`${byChc[c.id]?.total ?? 0} machines · ${byChc[c.id]?.available ?? 0} free`}
              />
            ))}
          </div>

          <Card
            title={selectedChc ? 'Machines at this centre' : 'All machines'}
            subtitle={`${rows.length} shown`}
          >
            <Table columns={COLUMNS} rows={rows} renderCell={renderCell} emptyLabel="No machines" />
          </Card>
        </>
      )}
    </div>
  )
}

function ChcTile({ active, onClick, name, sub, location }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-xl border p-4 text-left transition-colors ${
        active ? 'border-emerald-500 bg-emerald-50' : 'border-slate-200 bg-white hover:bg-slate-50'
      }`}
    >
      <div className="text-sm font-semibold text-slate-900">{name}</div>
      {location && <div className="text-xs text-slate-500">{location}</div>}
      <div className="mt-1 text-xs text-slate-600">{sub}</div>
    </button>
  )
}
