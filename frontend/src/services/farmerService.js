import apiClient from '../lib/apiClient'

// Farmer identity + a farmer's fields. Used by the farmer request screens.
export const farmerService = {
  getFarmers: (params = { limit: 200 }) =>
    apiClient.get('/farmers', { params }).then((r) => r.data),
  getFields: (farmerId) =>
    apiClient
      .get('/fields', { params: farmerId ? { farmer_id: farmerId } : {} })
      .then((r) => r.data),
}
