import { useQuery } from '@tanstack/react-query'

import { mapService } from '../services/mapService'

export function useMapMachines() {
  return useQuery({ queryKey: ['map', 'machines'], queryFn: mapService.getMachines })
}

export function useMapShortages() {
  return useQuery({ queryKey: ['map', 'shortages'], queryFn: mapService.getShortages })
}
