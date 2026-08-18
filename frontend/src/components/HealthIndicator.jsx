import { useHealth } from '../hooks/useHealth'

// Small green/red dot in the top bar reflecting the FastAPI backend status.
export default function HealthIndicator() {
  const { data, isError, isLoading } = useHealth()
  const online = !isError && !isLoading && data?.status === 'healthy'
  const color = isLoading ? 'bg-slate-300' : online ? 'bg-emerald-500' : 'bg-red-500'
  const label = isLoading ? 'checking' : online ? 'API online' : 'API offline'
  return (
    <div className="flex items-center gap-2 text-xs text-slate-500" title={label}>
      <span className={`h-2 w-2 rounded-full ${color}`} />
      <span className="hidden sm:inline">{label}</span>
    </div>
  )
}
