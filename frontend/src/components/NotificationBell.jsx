import { useEffect, useRef, useState } from 'react'
import { Bell } from 'lucide-react'

import { useUnreadCount } from '../hooks/useNotifications'
import NotificationList from './NotificationList'

export default function NotificationBell() {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const { data } = useUnreadCount()
  const unread = data?.unread ?? 0

  // Close the dropdown on an outside click or Escape.
  useEffect(() => {
    if (!open) return undefined
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100"
        aria-label={unread ? `Notifications (${unread} unread)` : 'Notifications'}
        title="Notifications"
      >
        <Bell size={18} />
        {unread > 0 && (
          <span
            className="absolute -right-0.5 -top-0.5 grid min-w-[18px] place-items-center rounded-full bg-red-500 px-1 text-[10px] font-semibold leading-none text-white"
            style={{ height: 18 }}
          >
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>
      {open && <NotificationList onClose={() => setOpen(false)} />}
    </div>
  )
}
