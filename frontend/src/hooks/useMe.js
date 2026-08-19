import { useQuery } from '@tanstack/react-query'

import { meService } from '../services/meService'

// The logged-in farmer's own fields (owner-scoped by the backend via the JWT).
export function useMyFields(enabled = true) {
  return useQuery({
    queryKey: ['me', 'fields'],
    queryFn: () => meService.getFields(),
    enabled,
  })
}

// Read-only machine assignment for one of the farmer's own requests.
export function useMyAssignment(requestId, enabled = true) {
  return useQuery({
    queryKey: ['me', 'assignment', requestId ?? 'none'],
    queryFn: () => meService.getAssignment(requestId),
    enabled: enabled && Boolean(requestId),
  })
}
