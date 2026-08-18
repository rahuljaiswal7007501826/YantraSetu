import { useMutation, useQuery } from '@tanstack/react-query'

import { routeService } from '../services/routeService'

export function useOptimizeRoute() {
  return useMutation({ mutationFn: (payload) => routeService.optimize(payload) })
}

export function useRoute(id) {
  return useQuery({
    queryKey: ['route', id],
    queryFn: () => routeService.get(id),
    enabled: Boolean(id),
  })
}
