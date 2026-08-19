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


// --- Phase 16: manager assignment workflow mutations ---
export function useAssignRequest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, machineId = null, useRecommendation = false }) =>
      requestService.assign(id, { machine_id: machineId, use_recommendation: useRecommendation }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['requests'] })
      qc.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}

export function useRejectRequest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }) => requestService.reject(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['requests'] })
      qc.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}

export function useCancelRequest() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => requestService.cancel(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['requests'] })
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['me'] })
    },
  })
}
