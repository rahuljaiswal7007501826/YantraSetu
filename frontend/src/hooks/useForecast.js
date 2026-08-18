import { useQuery } from '@tanstack/react-query'

import { forecastService } from '../services/forecastService'

// All (cluster, machine-type) demand insights, sorted by shortage risk (backend).
export function useForecast() {
  return useQuery({
    queryKey: ['forecast'],
    queryFn: forecastService.getForecast,
  })
}

// Only the HIGH/CRITICAL entries (used later; the Demand page derives these
// client-side from useForecast to avoid a second round-trip).
export function useShortages(minRisk = 'HIGH') {
  return useQuery({
    queryKey: ['shortages', minRisk],
    queryFn: () => forecastService.getShortages(minRisk),
  })
}
