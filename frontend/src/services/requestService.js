import apiClient from '../lib/apiClient'

export const requestService = {
  list: (params = {}) => apiClient.get('/requests', { params }).then((r) => r.data),
  get: (id) => apiClient.get(`/requests/${id}`).then((r) => r.data),
  create: (payload) => apiClient.post('/requests', payload).then((r) => r.data),
  // Phase 16 - manager assignment workflow.
  assign: (id, body) => apiClient.post(`/requests/${id}/assign`, body).then((r) => r.data),
  reject: (id, reason) => apiClient.post(`/requests/${id}/reject`, { reason }).then((r) => r.data),
  cancel: (id) => apiClient.post(`/requests/${id}/cancel`).then((r) => r.data),
}
