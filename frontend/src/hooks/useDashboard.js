import { useQuery } from '@tanstack/react-query'

import { dashboardService } from '../services/dashboardService'

export function useDashboard() {
  return useQuery({ queryKey: ['dashboard', 'admin'], queryFn: dashboardService.getAdmin })
}
