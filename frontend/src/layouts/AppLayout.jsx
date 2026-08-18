import { useState } from 'react'
import { Outlet } from 'react-router-dom'

import Sidebar from '../components/Sidebar'
import TopBar from '../components/TopBar'
import DemoOverlay from '../components/demo/DemoOverlay'

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      {/* Mobile overlay behind the drawer */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />

      <div className="md:pl-64">
        <TopBar onToggleSidebar={() => setSidebarOpen((o) => !o)} />
        <main className="p-4 md:p-6">
          <Outlet />
        </main>
      </div>

      {/* Guided SIH walkthrough - floats above every screen when running. */}
      <DemoOverlay />
    </div>
  )
}
