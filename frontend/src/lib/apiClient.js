import axios from 'axios'

import { API_URL } from './apiConfig'
import { clearToken, getToken } from './authToken'

// Single Axios instance for all backend calls.
//   - Local dev: API_URL is '' so baseURL is '/api' and Vite's dev proxy
//     forwards to FastAPI (unchanged behaviour).
//   - Production: set VITE_API_URL so calls target the deployed backend.
const apiClient = axios.create({
  baseURL: `${API_URL}/api`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 20000,
})

// Attach the JWT (if we have one) to every request in ONE place - no page or
// service needs to know about auth.
apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Normalize errors so every screen receives a consistent { status, message }.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status ?? 0
    // A 401 means the token is missing / expired / invalid: drop it and let the
    // app fall back to the login screen. (The login request carries no token, so
    // for a failed login this just clears an already-absent one.)
    if (status === 401) {
      clearToken()
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('auth:unauthorized'))
      }
    }
    const detail = error.response?.data?.detail
    return Promise.reject({
      status,
      message: detail || error.message || 'Request failed',
      raw: error,
    })
  },
)

export default apiClient
