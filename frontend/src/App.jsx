import { useEffect, useState } from 'react'

// During dev, the Vite proxy (see vite.config.js) forwards these paths to the
// FastAPI backend, so we can use relative URLs and avoid CORS in development.
const HEALTH_URL = '/health'

export default function App() {
  const [status, setStatus] = useState('checking')
  const [detail, setDetail] = useState(null)

  useEffect(() => {
    fetch(HEALTH_URL)
      .then((r) => {
        if (!r.ok) throw new Error('bad status')
        return r.json()
      })
      .then((data) => {
        setStatus('healthy')
        setDetail(data)
      })
      .catch(() => setStatus('unreachable'))
  }, [])

  const badgeClass = {
    checking: 'bg-slate-200 text-slate-700',
    healthy: 'bg-green-100 text-green-800',
    unreachable: 'bg-red-100 text-red-800',
  }[status]

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-emerald-600 font-bold text-white">
            YS
          </div>
          <div>
            <h1 className="text-xl font-semibold">YantraSetu</h1>
            <p className="text-sm text-slate-500">The Bridge of Machines</p>
          </div>
        </div>

        <p className="mt-5 text-sm text-slate-600">
          Intelligent agricultural machinery allocation &amp; rebalancing
          platform for Custom Hiring Centres.
        </p>

        <div className="mt-6 flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
          <span className="text-sm font-medium">Backend status</span>
          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${badgeClass}`}>
            {status}
          </span>
        </div>

        {detail && (
          <p className="mt-2 text-xs text-slate-400">environment: {detail.env}</p>
        )}

        <p className="mt-6 text-xs text-slate-400">
          Phase 0 - environment setup complete.
        </p>
      </div>
    </div>
  )
}
