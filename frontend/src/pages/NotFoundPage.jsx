import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold text-slate-900">Page not found</h1>
      <p className="text-sm text-slate-500">That route doesn&apos;t exist.</p>
      <Link to="/" className="text-sm font-medium text-emerald-700 hover:underline">
        Back to Overview
      </Link>
    </div>
  )
}
