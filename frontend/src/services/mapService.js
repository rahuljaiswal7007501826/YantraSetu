import apiClient from '../lib/apiClient'

export const mapService = {
  getMachines: () => apiClient.get('/map/machines').then((r) => r.data),
  getShortages: () => apiClient.get('/map/shortages').then((r) => r.data),
}
