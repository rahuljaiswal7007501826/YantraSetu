import apiClient from '../lib/apiClient'

export const requestService = {
  list: (params = {}) => apiClient.get('/requests', { params }).then((r) => r.data),
  get: (id) => apiClient.get(`/requests/${id}`).then((r) => r.data),
  create: (payload) => apiClient.post('/requests', payload).then((r) => r.data),
}
