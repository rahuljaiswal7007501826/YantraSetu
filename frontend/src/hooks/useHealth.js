import { useQuery } from '@tanstack/react-query'

import { getHealth } from '../services/healthService'

// Polls the backend health probe every 30s to drive the status dot in the top bar.
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
    retry: false,
    staleTime: 10_000,
  })
}
