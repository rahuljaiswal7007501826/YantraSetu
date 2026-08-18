import { Menu, PlayCircle } from 'lucide-react'

import { useDemo } from '../context/DemoContext'
import { useRole, ROLES } from '../context/RoleContext'
import Button from './ui/Button'
import HealthIndicator from './HealthIndicator'

export default function TopBar({ onToggleSidebar }) {
  const { role, setRole } = useRole()
  const demo = useDemo()

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

        {/* Role switcher - stands in for login until real auth exists. */}
        <label className="flex items-center gap-2 text-xs text-slate-500">
          <span className="hidden md:inline">View as</span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none"
          >
            {Object.entries(ROLES).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <Button onClick={demo.start} title="Run the deterministic SIH demo (Phase 7.7)">
          <PlayCircle size={16} />
          <span className="hidden sm:inline">Run Demo</span>
        </Button>
      </div>
    </header>
  )
}
