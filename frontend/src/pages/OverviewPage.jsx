import { Link } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  Building2,
  Coins,
  FileClock,
  PlusCircle,
  Shuffle,
  Tractor,
  Users,
} from 'lucide-react'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import KpiCard from '../components/ui/KpiCard'
import ErrorState from '../components/states/ErrorState'
import { SkeletonCard } from '../components/states/Loading'
import { useRole } from '../context/RoleContext'
import { useDashboard } from '../hooks/useDashboard'

const rupees = (n) => `Rs ${Math.round(n ?? 0).toLocaleString('en-IN')}`

export default function OverviewPage() {
  const { role } = useRole()
  // Farmers don't manage the network - give them a task-focused landing.
  if (role === 'farmer') return <FarmerHome />
  return <AdminOverview role={role} />
}

function FarmerHome() {
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Welcome</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Raise a machinery request and track the machine assigned to your field.
        </p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card title="Need a machine?" subtitle="Tell us the operation and date">
          <p className="text-sm text-slate-600">
            Create a request and the network finds the best available machine for your field.
          </p>
          <Link to="/new-request" className="mt-4 inline-block">
            <Button>
              <PlusCircle size={16} /> New request
            </Button>
          </Link>
        </Card>
        <Card title="Your activity" subtitle="Requests and bookings">
          <p className="text-sm text-slate-600">
            Check the status of your requests and the machine assigned to you.
          </p>
          <div className="mt-4 flex gap-2">
            <Link to="/my-requests">
              <Button variant="secondary">My requests</Button>
            </Link>
            <Link to="/my-booking">
              <Button variant="secondary">My booking</Button>
            </Link>
          </div>
        </Card>
      </div>
    </div>
  )
}

function AdminOverview({ role }) {
  const { data: d, isLoading, isError, error, refetch } = useDashboard()
  const title = role === 'chc_operator' ? 'My CHC' : 'Network Overview'

  if (isLoading) {
    return (
      <Shell title={title}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </Shell>
    )
  }
  if (isError) {
    return (
      <Shell title={title}>
        <ErrorState message={error?.message || 'Failed to load the dashboard.'} onRetry={refetch} />
      </Shell>
    )
  }

  return (
    <Shell title={title}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="CHCs" value={d.total_chcs} icon={Building2} accent="slate" />
        <KpiCard label="Machines" value={d.total_machines} icon={Tractor} accent="emerald" />
        <KpiCard label="Farmers" value={d.total_farmers} icon={Users} accent="blue" />
        <KpiCard label="Pending requests" value={d.pending_requests} icon={FileClock} accent="amber" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Machine status (today)" className="lg:col-span-2">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatusTile label="Available" value={d.machines_available} dot="bg-emerald-500" />
            <StatusTile label="Booked" value={d.machines_booked} dot="bg-amber-500" />
            <StatusTile label="In transit" value={d.machines_in_transit} dot="bg-blue-500" />
            <StatusTile label="Maintenance" value={d.machines_maintenance} dot="bg-slate-400" />
          </div>
        </Card>
        <Card title="Needs attention">
          <div className="space-y-3">
            <AttnRow
              icon={AlertTriangle}
              tone="text-red-600"
              value={d.critical_shortages}
              label="Critical shortages"
              to="/demand"
              cta="View demand"
            />
            <AttnRow
              icon={Shuffle}
              tone="text-amber-600"
              value={d.pending_relocations}
              label="Pending relocations"
              to="/relocations"
              cta="Review"
            />
          </div>
        </Card>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <KpiCard
          label="High-risk areas"
          value={d.high_risk_areas}
          icon={Activity}
          accent="red"
          hint="HIGH or CRITICAL shortage risk"
        />
        <KpiCard
          label="Potential net benefit"
          value={rupees(d.potential_net_benefit)}
          icon={Coins}
          accent="emerald"
          hint="from pending relocation moves"
        />
      </div>
    </Shell>
  )
}

function Shell({ title, children }) {
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Network health and the decisions that need attention.
        </p>
      </header>
      {children}
    </div>
  )
}

function StatusTile({ label, value, dot }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center gap-1.5 text-xs text-slate-500">
        <span className={`h-2 w-2 rounded-full ${dot}`} />
        {label}
      </div>
      <div className="mt-1 text-xl font-semibold text-slate-900">{value}</div>
    </div>
  )
}

function AttnRow({ icon: Icon, tone, value, label, to, cta }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 p-3">
      <div className="flex items-center gap-2">
        <Icon size={18} className={tone} />
        <div>
          <div className="text-sm font-semibold text-slate-900">{value}</div>
          <div className="text-xs text-slate-500">{label}</div>
        </div>
      </div>
      <Link to={to} className="text-xs font-medium text-emerald-700 hover:underline">
        {cta} &rarr;
      </Link>
    </div>
  )
}
