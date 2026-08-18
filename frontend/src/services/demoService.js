import apiClient from '../lib/apiClient'

// Rewinds the relocation approve/reject action so the guided demo can re-run.
export const demoService = {
  reset: () => apiClient.post('/demo/reset').then((r) => r.data),
}
