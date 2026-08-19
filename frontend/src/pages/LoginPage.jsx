import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { LogIn } from 'lucide-react'

import Button from '../components/ui/Button'
import { LANDING_BY_ROLE, useRole } from '../context/RoleContext'

// Seeded by `python seed_users.py` (see backend). Shared password for the demo.
const DEMO_USERS = [
  { label: 'District Admin', email: 'admin@yantrasetu.demo' },
  { label: 'CHC Manager', email: 'manager@yantrasetu.demo' },
  { label: 'Operator', email: 'operator@yantrasetu.demo' },
  { label: 'Farmer', email: 'farmer@yantrasetu.demo' },
]
const DEMO_PASSWORD = 'demo1234'
const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-emerald-500 focus:outline-none'

export default function LoginPage() {
  const { login, isAuthenticated, role, loading } = useRole()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  // Already signed in? Skip the form.
  if (!loading && isAuthenticated) {
    return <Navigate to={LANDING_BY_ROLE[role] ?? '/'} replace />
  }

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const u = await login(email.trim(), password)
      navigate(LANDING_BY_ROLE[u.role] ?? '/', { replace: true })
    } catch (err) {
      setError(err?.message || 'Login failed. Check your email and password.')
    } finally {
      setSubmitting(false)
    }
  }

  const quickFill = (demoEmail) => {
    setEmail(demoEmail)
    setPassword(DEMO_PASSWORD)
    setError(null)
  }

  return (
    <div className="grid min-h-screen place-items-center bg-slate-100 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-emerald-600 text-lg font-bold text-white">
            YS
          </div>
          <div>
            <div className="text-lg font-semibold text-slate-900">YantraSetu</div>
            <div className="text-xs text-slate-500">The Bridge of Machines</div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-base font-semibold text-slate-900">Sign in</h1>
          <p className="mt-0.5 text-sm text-slate-500">Access your YantraSetu dashboard.</p>

          <form onSubmit={submit} className="mt-5 space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-600">Email</label>
              <input
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputCls}
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-600">Password</label>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputCls}
                required
              />
            </div>

            {error && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            )}

            <Button type="submit" disabled={submitting} className="w-full">
              <LogIn size={16} />
              {submitting ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>

          <div className="mt-6 border-t border-slate-100 pt-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-400">
              Demo accounts
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Click to fill, then Sign in. Shared password:{' '}
              <code className="rounded bg-slate-100 px-1">demo1234</code>
            </p>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {DEMO_USERS.map((u) => (
                <button
                  key={u.email}
                  type="button"
                  onClick={() => quickFill(u.email)}
                  className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-left text-xs text-slate-600 hover:border-emerald-400 hover:bg-emerald-50"
                >
                  {u.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-slate-400">
          Synthetic demo data - Smart India Hackathon
        </p>
      </div>
    </div>
  )
}
