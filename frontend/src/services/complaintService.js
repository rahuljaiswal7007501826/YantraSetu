import apiClient from '../lib/apiClient'

export const complaintService = {
  // Farmer
  create: (payload) => apiClient.post('/complaints', payload).then((r) => r.data),
  listMine: () => apiClient.get('/me/complaints').then((r) => r.data),
  // Staff (role-gated on the backend). CHC id is an explicit filter for managers;
  // admins can list everything.
  listByChc: (chcId, params = {}) =>
    apiClient.get(`/chc/${chcId}/complaints`, { params }).then((r) => r.data),
  listAll: (params = {}) => apiClient.get('/admin/complaints', { params }).then((r) => r.data),
  respond: (id, response) =>
    apiClient.post(`/complaints/${id}/respond`, { response }).then((r) => r.data),
  resolve: (id) => apiClient.post(`/complaints/${id}/resolve`).then((r) => r.data),
  close: (id) => apiClient.post(`/complaints/${id}/close`).then((r) => r.data),
}
