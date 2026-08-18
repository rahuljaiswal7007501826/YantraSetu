import { useQuery } from '@tanstack/react-query'

import { farmerService } from '../services/farmerService'

export function useFarmers() {
  return useQuery({
    queryKey: ['farmers'],
    queryFn: () => farmerService.getFarmers({ limit: 200 }),
  })
}

export function useFields(farmerId) {
  return useQuery({
    queryKey: ['fields', farmerId ?? 'none'],
    queryFn: () => farmerService.getFields(farmerId),
    enabled: Boolean(farmerId),
  })
}
