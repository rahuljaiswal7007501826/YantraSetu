const STATUS_STYLES = {
  available: 'bg-emerald-100 text-emerald-800',
  operational: 'bg-emerald-100 text-emerald-800',
  booked: 'bg-amber-100 text-amber-800',
  in_transit: 'bg-blue-100 text-blue-800',
  maintenance: 'bg-slate-200 text-slate-700',
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  // Complaint lifecycle (Phase 19).
  open: 'bg-amber-100 text-amber-800',
  in_progress: 'bg-blue-100 text-blue-800',
  resolved: 'bg-emerald-100 text-emerald-800',
  closed: 'bg-slate-200 text-slate-600',
  allocated: 'bg-emerald-100 text-emerald-800',
  scheduled: 'bg-blue-100 text-blue-800',
  rejected: 'bg-red-100 text-red-800',
  cancelled: 'bg-slate-200 text-slate-600',
  completed: 'bg-blue-100 text-blue-800',
  optimized: 'bg-blue-100 text-blue-800',
  active: 'bg-emerald-100 text-emerald-800',
  voided: 'bg-slate-200 text-slate-600',
}

export default function StatusBadge({ status }) {
  const cls = STATUS_STYLES[status] || 'bg-slate-100 text-slate-700'
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${cls}`}>
      {String(status || '').replace(/_/g, ' ')}
    </span>
  )
}
