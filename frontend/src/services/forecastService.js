import apiClient from '../lib/apiClient'

// Thin wrappers over the demand-forecast endpoints. No logic here - the backend
// demand engine is the source of truth.
export const forecastService = {
  getForecast: () => apiClient.get('/forecast').then((r) => r.data),
  getShortages: (minRisk) =>
    apiClient
      .get('/forecast/shortages', { params: minRisk ? { min_risk: minRisk } : {} })
      .then((r) => r.data),
}
