import apiClient from '../lib/apiClient'

// Farmer self-service. The backend derives the farmer's identity from the JWT,
// so these never take a farmer_id from the client.
export const meService = {
  getFields: () => apiClient.get('/me/fields').then((r) => r.data),
  getAssignment: (requestId) =>
    apiClient.get(`/me/requests/${requestId}/assignment`).then((r) => r.data),
}
