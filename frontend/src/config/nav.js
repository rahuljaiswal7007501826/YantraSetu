import {
  Activity,
  BarChart3,
  CalendarClock,
  FileText,
  Inbox,
  LayoutDashboard,
  Map,
  MessageSquare,
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
    { label: 'Pending Requests', to: '/pending-requests', icon: Inbox },
    { label: 'Relocations', to: '/relocations', icon: Shuffle },
    { label: 'Live Map', to: '/map', icon: Map },
    { label: 'CHCs & Machines', to: '/network', icon: Tractor },
    { label: 'Analytics', to: '/analytics', icon: BarChart3 },
    { label: 'Complaints', to: '/complaints', icon: MessageSquare },
  ],
  // CHC manager: the network Overview and Analytics are district-admin only
  // (RBAC), so the manager's workspace centres on the relocation approvals,
  // fleet, routes and the shared map.
  chc_operator: [
    { label: 'Pending Requests', to: '/pending-requests', icon: Inbox },
    { label: 'Relocation Approvals', to: '/relocations', icon: Shuffle },
    { label: 'Machines', to: '/network', icon: Tractor },
    { label: 'Routes', to: '/routes', icon: RouteIcon },
    { label: 'Live Map', to: '/map', icon: Map },
    { label: 'Complaints', to: '/complaints', icon: MessageSquare },
  ],
  // Machine/route operator: operational read + route execution only.
  operator: [
    { label: 'Machines', to: '/network', icon: Tractor },
    { label: 'Routes', to: '/routes', icon: RouteIcon },
    { label: 'Live Map', to: '/map', icon: Map },
  ],
  farmer: [
    { label: 'My Requests', to: '/my-requests', icon: FileText },
    { label: 'New Request', to: '/new-request', icon: PlusCircle },
    { label: 'My Booking', to: '/my-booking', icon: CalendarClock },
    { label: 'Complaints', to: '/my-complaints', icon: MessageSquare },
  ],
}
