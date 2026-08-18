import { BrowserRouter, Route, Routes } from 'react-router-dom'

import AppLayout from './layouts/AppLayout'
import AllocationPage from './pages/AllocationPage'
import AnalyticsPage from './pages/AnalyticsPage'
import DemandPage from './pages/DemandPage'
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

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/demand" element={<DemandPage />} />
          <Route path="/allocation" element={<AllocationPage />} />
          <Route path="/relocations" element={<RelocationsPage />} />
          <Route path="/routes" element={<RoutesPage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/network" element={<NetworkPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/my-requests" element={<MyRequestsPage />} />
          <Route path="/request/:id" element={<RequestDetailsPage />} />
          <Route path="/new-request" element={<NewRequestPage />} />
          <Route path="/my-booking" element={<MyBookingPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
