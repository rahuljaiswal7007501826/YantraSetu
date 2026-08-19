import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useRole } from '../context/RoleContext'
import { notificationService } from '../services/notificationService'

// Poll so the bell "feels live" without any WebSocket infrastructure. Pausing in
// the background (refetchIntervalInBackground: false) avoids needless requests
// when the tab isn't visible. Only runs while authenticated.
const POLL_MS = 15_000

// Cheap badge count - polled on its own so it can stay light even while the
// full list isn't open.
export function useUnreadCount() {
  const { isAuthenticated } = useRole()
  return useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: () => notificationService.unreadCount(),
    enabled: isAuthenticated,
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: false,
  })
}

// Full list - typically enabled only while the dropdown is open.
export function useNotifications({ unreadOnly = false, limit = 20, enabled = true } = {}) {
  const { isAuthenticated } = useRole()
  return useQuery({
    queryKey: ['notifications', 'list', { unreadOnly, limit }],
    queryFn: () => notificationService.list({ unread_only: unreadOnly, limit }),
    enabled: isAuthenticated && enabled,
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: false,
  })
}

export function useMarkNotificationRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => notificationService.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => notificationService.markAllRead(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })
}
