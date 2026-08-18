import { useMutation, useQueryClient } from '@tanstack/react-query'

import { demoService } from '../services/demoService'

// Reset touches relocations, machine status (map), the forecast and the
// dashboard - so we refresh everything to put every screen back to the start.
export function useDemoReset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => demoService.reset(),
    onSuccess: () => qc.invalidateQueries(),
  })
}
