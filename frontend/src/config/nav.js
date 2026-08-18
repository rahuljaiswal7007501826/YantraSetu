import {
  Activity,
  BarChart3,
  CalendarClock,
  FileText,
  LayoutDashboard,
  Map,
  PlusCircle,
  Route as RouteIcon,
  Shuffle,
  Tractor,
} from 'lucide-react'

// Role-aware sidebar. Note: "Machine Allocation" (/allocation) is intentionally
// NOT a nav item - it is reached along the golden path (a button on the Demand
// and Relocation screens), not browsed to directly.
export const NAV_BY_ROLE = {
  district_admin: [
    { label: 'Overview', to: '/', icon: LayoutDashboard },
    { label: 'Demand Intelligence', to: '/demand', icon: Activity },
    { label: 'Relocations', to: '/relocations', icon: Shuffle },
    { label: 'Live Map', to: '/map', icon: Map },
    { label: 'CHCs & Machines', to: '/network', icon: Tractor },
    { label: 'Analytics', to: '/analytics', icon: BarChart3 },
  ],
  chc_operator: [
    { label: 'My CHC', to: '/', icon: LayoutDashboard },
    { label: 'Machines', to: '/network', icon: Tractor },
    { label: 'Relocation Approvals', to: '/relocations', icon: Shuffle },
    { label: 'Routes', to: '/routes', icon: RouteIcon },
    { label: 'Analytics', to: '/analytics', icon: BarChart3 },
  ],
  farmer: [
    { label: 'My Requests', to: '/my-requests', icon: FileText },
    { label: 'New Request', to: '/new-request', icon: PlusCircle },
    { label: 'My Booking', to: '/my-booking', icon: CalendarClock },
  ],
}
