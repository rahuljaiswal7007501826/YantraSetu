import { QueryClient } from '@tanstack/react-query'

// Central React Query config. Sensible defaults for a dashboard: don't hammer
// the API on window focus, keep data fresh for 30s, retry once on failure.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
})
