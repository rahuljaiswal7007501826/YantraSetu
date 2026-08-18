import { Inbox } from 'lucide-react'

export default function EmptyState({ title = 'Nothing here yet', description, icon: Icon = Inbox, action }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center">
      <Icon className="text-slate-400" />
      <h3 className="text-sm font-medium text-slate-700">{title}</h3>
      {description && <p className="max-w-md text-xs text-slate-500">{description}</p>}
      {action}
    </div>
  )
}
