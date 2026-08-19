import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { complaintService } from '../services/complaintService'

export function useMyComplaints() {
  return useQuery({
    queryKey: ['complaints', 'mine'],
    queryFn: () => complaintService.listMine(),
  })
}

export function useChcComplaints(chcId, params = {}) {
  return useQuery({
    queryKey: ['complaints', 'chc', chcId, params],
    queryFn: () => complaintService.listByChc(chcId, params),
    enabled: Boolean(chcId),
  })
}

export function useAllComplaints(params = {}, options = {}) {
  return useQuery({
    queryKey: ['complaints', 'all', params],
    queryFn: () => complaintService.listAll(params),
    ...options,
  })
}

export function useCreateComplaint() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload) => complaintService.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['complaints'] })
      qc.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}

// Shared invalidation for the staff status-transition actions.
function useComplaintAction(mutationFn) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['complaints'] })
      qc.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}

export function useRespondComplaint() {
  return useComplaintAction(({ id, response }) => complaintService.respond(id, response))
}

export function useResolveComplaint() {
  return useComplaintAction((id) => complaintService.resolve(id))
}

export function useCloseComplaint() {
  return useComplaintAction((id) => complaintService.close(id))
}
