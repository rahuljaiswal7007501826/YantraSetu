import { LogOut, Menu, PlayCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { useDemo } from '../context/DemoContext'
import { ROLES, useRole } from '../context/RoleContext'
import Button from './ui/Button'
import HealthIndicator from './HealthIndicator'
import NotificationBell from './NotificationBell'

export default function TopBar({ onToggleSidebar }) {
  const { user, role, logout } = useRole()
  const demo = useDemo()
  const navigate = useNavigate()

  const onLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur md:px-6">
      <button
        className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 md:hidden"
        onClick={onToggleSidebar}
        aria-label="Toggle navigation"
      >
        <Menu size={20} />
      </button>

      <div className="ml-auto flex items-center gap-3 md:gap-4">
        <HealthIndicator />

        <Button onClick={demo.start} title="Run the deterministic SIH demo">
          <PlayCircle size={16} />
          <span className="hidden sm:inline">Run Demo</span>
        </Button>

        {/* In-app notifications (same component for every role; owner-scoped server-side). */}
        <NotificationBell />

        {/* Signed-in user + logout (replaces the old mock role switcher). */}
        <div className="flex items-center gap-3 border-l border-slate-200 pl-3">
          <div className="hidden text-right sm:block">
            <div className="text-sm font-medium text-slate-800">{user?.name}</div>
            <div className="text-[11px] text-slate-400">{ROLES[role] ?? ''}</div>
          </div>
          <Button variant="secondary" onClick={onLogout} title="Log out">
            <LogOut size={16} />
            <span className="hidden sm:inline">Logout</span>
          </Button>
        </div>
      </div>
    </header>
  )
}
