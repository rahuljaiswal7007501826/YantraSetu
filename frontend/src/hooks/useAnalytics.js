import { useQuery } from '@tanstack/react-query'

import { analyticsService } from '../services/analyticsService'

export function useAnalyticsSummary() {
  return useQuery({ queryKey: ['analytics', 'summary'], queryFn: analyticsService.getSummary })
}

export function useAnalyticsImpact() {
  return useQuery({ queryKey: ['analytics', 'impact'], queryFn: analyticsService.getImpact })
}

export function useAnalyticsUtilization() {
  return useQuery({
    queryKey: ['analytics', 'utilization'],
    queryFn: analyticsService.getUtilization,
  })
}
