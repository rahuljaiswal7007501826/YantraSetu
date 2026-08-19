import { useEffect } from 'react'

import { useRole } from '../context/RoleContext'
import { useFarmers } from '../hooks/useFarmers'

/**
 * Farmer identity selector.
 *
 *  - Logged-in FARMER: acts as themselves. We do NOT call /api/farmers (it's
 *    staff-only now) - the identity is locked to their linked profile and we
 *    push it up via onChange so the farmer screens work with owner-scoping.
 *  - Staff (admin / manager): keep the picker so they can inspect any farmer.
 */
export default function FarmerPicker({ value, onChange, label = 'Acting as' }) {
  const { role } = useRole()
  if (role === 'farmer') return <FarmerSelf value={value} onChange={onChange} />
  return <StaffPicker value={value} onChange={onChange} label={label} />
}

function FarmerSelf({ value, onChange }) {
  const { user } = useRole()
  const farmerId = user?.farmerId ?? null

  // Lock the selection to the logged-in farmer's own profile.
  useEffect(() => {
    if (farmerId && value !== farmerId) onChange(farmerId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [farmerId])

  return (
    <span className="text-xs font-medium text-slate-500">
      {user?.name}
      {farmerId ? ` · Farmer #${farmerId}` : ' · no linked profile'}
    </span>
  )
}

function StaffPicker({ value, onChange, label }) {
  const { data: farmers = [], isLoading } = useFarmers()
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={isLoading}
        className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 disabled:opacity-60"
      >
        {isLoading && <option>Loading...</option>}
        {!isLoading && farmers.length === 0 && <option>No farmers</option>}
        {farmers.map((f) => (
          <option key={f.id} value={f.id}>
            #{f.id} · {f.name} ({f.village})
          </option>
        ))}
      </select>
    </label>
  )
}
