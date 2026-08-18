import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { requestService } from '../services/requestService'

export function useRequests(params = {}) {
  return useQuery({
    queryKey: ['requests', params],
    queryFn: () => requestService.list(params),
  })
}

export function useRequest(id) {
  return useQuery({
    queryKey: ['request', id],
    queryFn: () => requestService.get(id),
    enabled: Boolean(id),
  })
}

export function useCreateRequest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload) => requestService.create(payload),
    onSuccess: () => {
      // A new request changes both the farmer's list and the admin roll-up.
      qc.invalidateQueries({ queryKey: ['requests'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
