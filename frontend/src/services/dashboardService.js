import apiClient from '../lib/apiClient'

// Network-wide KPI roll-up for the Overview screen.
export const dashboardService = {
  getAdmin: () => apiClient.get('/dashboard/admin').then((r) => r.data),
}
