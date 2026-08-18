import axios from 'axios'

// Single Axios instance for all backend calls. Vite proxies /api -> FastAPI.
// When real auth arrives, a request interceptor here can attach the JWT in ONE
// place, no page or service needs to change.
const apiClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 20000,
})

// Normalize errors so every screen receives a consistent { status, message }.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status ?? 0
    const detail = error.response?.data?.detail
    return Promise.reject({
      status,
      message: detail || error.message || 'Request failed',
      raw: error,
    })
  },
)

export default apiClient
