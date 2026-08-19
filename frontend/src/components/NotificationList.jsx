import { useNavigate } from 'react-router-dom'

import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from '../hooks/useNotifications'

// Tiny relative-time formatter (no date library in the project's deps).
function timeAgo(iso) {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''
  const s = Math.max(0, Math.floor((Date.now() - then) / 1000))
  if (s < 60) return 'just now'
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function NotificationList({ onClose }) {
  const navigate = useNavigate()
  const { data: items = [], isLoading, isError } = useNotifications({ limit: 20 })
  const markRead = useMarkNotificationRead()
  const markAll = useMarkAllNotificationsRead()

  const onRowClick = (n) => {
    if (!n.is_read) markRead.mutate(n.id)
    if (n.link) {
      navigate(n.link)
      onClose?.()
    }
  }

  return (
    <div className="absolute right-0 z-40 mt-2 w-80 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl ring-1 ring-black/5">
      <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2">
        <span className="text-sm font-semibold text-slate-800">Notifications</span>
        <button
          onClick={() => markAll.mutate()}
          disabled={markAll.isPending}
          className="text-xs font-medium text-emerald-600 hover:text-emerald-700 disabled:opacity-50"
        >
          Mark all read
        </button>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {isLoading ? (
          <p className="px-3 py-6 text-center text-sm text-slate-400">Loading...</p>
        ) : isError ? (
          <p className="px-3 py-6 text-center text-sm text-red-500">Could not load notifications.</p>
        ) : items.length === 0 ? (
          <p className="px-3 py-6 text-center text-sm text-slate-400">You're all caught up.</p>
        ) : (
          items.map((n) => (
            <button
              key={n.id}
              onClick={() => onRowClick(n)}
              className={`flex w-full flex-col items-start gap-0.5 border-b border-slate-50 px-3 py-2.5 text-left hover:bg-slate-50 ${
                n.is_read ? '' : 'bg-emerald-50/40'
              }`}
            >
              <div className="flex w-full items-center gap-2">
                {!n.is_read && <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-500" />}
                <span className="flex-1 text-sm font-medium text-slate-800">{n.title}</span>
                <span className="shrink-0 text-[11px] text-slate-400">{timeAgo(n.created_at)}</span>
              </div>
              <span className="text-xs text-slate-500">{n.body}</span>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
