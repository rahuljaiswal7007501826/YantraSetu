import apiClient from '../lib/apiClient'

export const relocationService = {
  list: (status) =>
    apiClient.get('/relocations', { params: status ? { status } : {} }).then((r) => r.data),
  get: (id) => apiClient.get(`/relocations/${id}`).then((r) => r.data),
  generate: () => apiClient.post('/relocations/generate').then((r) => r.data),
  approve: (id) => apiClient.post(`/relocations/${id}/approve`).then((r) => r.data),
  reject: (id) => apiClient.post(`/relocations/${id}/reject`).then((r) => r.data),
}
