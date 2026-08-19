import apiClient from '../lib/apiClient'

// In-app notifications for the current user. The backend owner-scopes every
// call to the JWT's user, so no user id is ever sent from the client.
export const notificationService = {
  list: (params = {}) => apiClient.get('/me/notifications', { params }).then((r) => r.data),
  unreadCount: () => apiClient.get('/me/notifications/unread-count').then((r) => r.data),
  markRead: (id) => apiClient.post(`/me/notifications/${id}/read`).then((r) => r.data),
  markAllRead: () => apiClient.post('/me/notifications/read-all').then((r) => r.data),
}
