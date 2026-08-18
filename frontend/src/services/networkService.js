import apiClient from '../lib/apiClient'

// CHCs and machines (fleet visibility).
export const networkService = {
  getChcs: () => apiClient.get('/chcs').then((r) => r.data),
  getMachines: (chcId) =>
    apiClient.get('/machines', { params: chcId ? { chc_id: chcId } : {} }).then((r) => r.data),
}
