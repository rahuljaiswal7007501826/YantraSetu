import apiClient from '../lib/apiClient'

// Read-only analytics. All numbers are computed by the backend engines; the
// frontend only visualizes them.
export const analyticsService = {
  getSummary: () => apiClient.get('/analytics/summary').then((r) => r.data),
  getImpact: () => apiClient.get('/analytics/impact').then((r) => r.data),
  getUtilization: () => apiClient.get('/analytics/utilization').then((r) => r.data),
}
