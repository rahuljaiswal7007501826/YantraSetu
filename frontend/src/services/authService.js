import apiClient from '../lib/apiClient'

// Authentication calls. Login returns { access_token, token_type }; /auth/me
// returns the current user (id, name, email, role, farmer_id, ...). The apiClient
// interceptor attaches the bearer token, so /me just works once we've stored one.
export const authService = {
  login: (email, password) =>
    apiClient.post('/auth/login', { email, password }).then((r) => r.data),
  me: () => apiClient.get('/auth/me').then((r) => r.data),
}
