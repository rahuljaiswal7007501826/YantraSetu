import { NavLink } from 'react-router-dom'

import { NAV_BY_ROLE } from '../config/nav'
import { useRole, ROLES } from '../context/RoleContext'

// Fixed sidebar on md+; slides in as a drawer on small screens.
export default function Sidebar({ open, onNavigate }) {
  const { role } = useRole()
  const items = NAV_BY_ROLE[role] || []

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-30 w-64 transform border-r border-slate-200 bg-white transition-transform duration-200 md:translate-x-0 ${
        open ? 'translate-x-0' : '-translate-x-full'
      }`}
    >
      <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-4">
        <div className="grid h-9 w-9 place-items-center rounded-lg bg-emerald-600 font-bold text-white">
          YS
        </div>
        <div>
          <div className="text-sm font-semibold text-slate-800">YantraSetu</div>
          <div className="text-[11px] text-slate-400">The Bridge of Machines</div>
        </div>
      </div>

      <div className="px-3 py-2 text-[11px] font-medium uppercase tracking-wide text-slate-400">
        {ROLES[role]}
      </div>

      <nav className="space-y-1 px-3">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'text-slate-600 hover:bg-slate-100'
              }`
            }
          >
            <item.icon size={18} />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
