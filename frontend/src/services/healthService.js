import { API_URL } from '../lib/apiConfig'

// The health probe lives at the backend root (/health), not under /api.
//   - Local dev: API_URL is '' -> relative '/health', forwarded by Vite's proxy.
//   - Production: VITE_API_URL + '/health'.
export async function getHealth() {
  const res = await fetch(`${API_URL}/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json()
}
