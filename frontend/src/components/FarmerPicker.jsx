import { useFarmers } from '../hooks/useFarmers'

/**
 * Farmer identity selector. Until real JWT auth exists, the farmer screens let
 * you "act as" a farmer by picking one here. Swapping in auth later means
 * replacing this with the logged-in farmer - the pages read a farmerId either way.
 */
export default function FarmerPicker({ value, onChange, label = 'Acting as' }) {
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
