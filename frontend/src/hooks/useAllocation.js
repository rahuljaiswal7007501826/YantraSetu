import { useQuery } from '@tanstack/react-query'

import { allocationService } from '../services/allocationService'

// Recommendations are read-only for a given request, so useQuery (keyed by the
// request id) is a natural fit even though the backend endpoint is a POST.
export function useAllocation(requestId, topN = 5) {
  return useQuery({
    queryKey: ['allocation', requestId, topN],
    queryFn: () => allocationService.recommend(requestId, topN),
    enabled: Boolean(requestId),
  })
}
