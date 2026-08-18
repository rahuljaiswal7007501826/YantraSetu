import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { relocationService } from '../services/relocationService'

// All recommendations (the page filters by status client-side so KPIs can see all).
export function useRelocations() {
  return useQuery({
    queryKey: ['relocations'],
    queryFn: () => relocationService.list(),
  })
}

// Operator actions. Approving changes a machine to in_transit, so we also
// invalidate the demand forecast (supply changed) to keep other screens honest.
export function useRelocationActions() {
  const qc = useQueryClient()

  const approve = useMutation({
    mutationFn: (id) => relocationService.approve(id),
    onSuccess: () => {
      // The machine goes in_transit, so every screen that shows machine state
      // (map, overview dashboard), supply (forecast) and impact (analytics)
      // must refresh too - this is what lets the demo's analytics payoff show
      // the newly approved relocation without a manual browser refresh.
      qc.invalidateQueries({ queryKey: ['relocations'] })
      qc.invalidateQueries({ queryKey: ['forecast'] })
      qc.invalidateQueries({ queryKey: ['map'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      qc.invalidateQueries({ queryKey: ['analytics'] })
    },
  })

  const reject = useMutation({
    mutationFn: (id) => relocationService.reject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['relocations'] }),
  })

  const generate = useMutation({
    mutationFn: () => relocationService.generate(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['relocations'] }),
  })

  return { approve, reject, generate }
}
