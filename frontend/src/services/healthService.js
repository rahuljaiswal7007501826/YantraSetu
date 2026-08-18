// The health probe lives at the backend root (/health), not under /api.
// Vite proxies /health to FastAPI, so a plain fetch is enough here.
export async function getHealth() {
  const res = await fetch('/health')
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
  return res.json()
}
