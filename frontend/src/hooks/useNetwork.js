import { useQuery } from '@tanstack/react-query'

import { networkService } from '../services/networkService'

export function useChcs() {
  return useQuery({ queryKey: ['chcs'], queryFn: networkService.getChcs })
}

export function useMachines(chcId) {
  return useQuery({
    queryKey: ['machines', chcId ?? 'all'],
    queryFn: () => networkService.getMachines(chcId),
  })
}
