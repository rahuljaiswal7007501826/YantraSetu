import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { useRole } from './context/RoleContext'
import AppLayout from './layouts/AppLayout'
import AllocationPage from './pages/AllocationPage'
import AnalyticsPage from './pages/AnalyticsPage'
import DemandPage from './pages/DemandPage'
import FarmerFileComplaint from './pages/FarmerFileComplaint'
import FarmerMyComplaints from './pages/FarmerMyComplaints'
import LoginPage from './pages/LoginPage'
import ManagerPendingRequests from './pages/ManagerPendingRequests'
import MapPage from './pages/MapPage'
import MyBookingPage from './pages/MyBookingPage'
import MyRequestsPage from './pages/MyRequestsPage'
import NetworkPage from './pages/NetworkPage'
import NewRequestPage from './pages/NewRequestPage'
import NotFoundPage from './pages/NotFoundPage'
import OverviewPage from './pages/OverviewPage'
import RelocationsPage from './pages/RelocationsPage'
import RequestDetailsPage from './pages/RequestDetailsPage'
import RoutesPage from './pages/RoutesPage'
import StaffComplaints from './pages/StaffComplaints'

// Gate the whole app behind authentication. While the token is being validated
// we show a lightweight splash so the login screen never flashes for a user who
// is actually signed in.
function RequireAuth({ children }) {
  const { isAuthenticated, loading } = useRole()
  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center bg-slate-50 text-sm text-slate-500">
        Loading YantraSetu...
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<OverviewPage />} />
          <Route path="/demand" element={<DemandPage />} />
          <Route path="/allocation" element={<AllocationPage />} />
          <Route path="/relocations" element={<RelocationsPage />} />
          <Route path="/routes" element={<RoutesPage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/network" element={<NetworkPage />} />
          <Route path="/pending-requests" element={<ManagerPendingRequests />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/my-requests" element={<MyRequestsPage />} />
          <Route path="/request/:id" element={<RequestDetailsPage />} />
          <Route path="/new-request" element={<NewRequestPage />} />
          <Route path="/my-booking" element={<MyBookingPage />} />
          <Route path="/file-complaint" element={<FarmerFileComplaint />} />
          <Route path="/my-complaints" element={<FarmerMyComplaints />} />
          <Route path="/complaints" element={<StaffComplaints />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
