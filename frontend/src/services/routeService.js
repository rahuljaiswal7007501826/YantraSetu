import apiClient from '../lib/apiClient'

export const routeService = {
  optimize: (payload) => apiClient.post('/routes/optimize', payload).then((r) => r.data),
  get: (id) => apiClient.get(`/routes/${id}`).then((r) => r.data),
}
