import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlusCircle } from 'lucide-react'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import ErrorState from '../components/states/ErrorState'
import FarmerPicker from '../components/FarmerPicker'
import { useFields } from '../hooks/useFarmers'
import { useCreateRequest } from '../hooks/useRequests'

// Operations the network can perform (each maps to a machine type on the backend).
const OPERATIONS = ['Harvesting', 'Ploughing', 'Tillage', 'Sowing', 'Spraying', 'Baling']
const URGENCIES = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High (urgent)' },
]
const TODAY = new Date().toISOString().slice(0, 10)

export default function NewRequestPage() {
  const navigate = useNavigate()
  const [farmerId, setFarmerId] = useState(null)
  const [fieldId, setFieldId] = useState('')
  const [operation, setOperation] = useState(OPERATIONS[0])
  const [date, setDate] = useState(TODAY)
  const [urgency, setUrgency] = useState('medium')

  const fieldsQ = useFields(farmerId)
  const fields = fieldsQ.data ?? []
  const create = useCreateRequest()

  // When the farmer changes, default to their first field.
  useEffect(() => {
    if (fields.length) setFieldId(String(fields[0].id))
    else setFieldId('')
  }, [fields])

  const canSubmit = Boolean(farmerId && fieldId && operation && date) && !create.isPending

  const onSubmit = (e) => {
    e.preventDefault()
    if (!canSubmit) return
    create.mutate(
      {
        farmer_id: farmerId,
        field_id: Number(fieldId),
        operation_type: operation,
        requested_date: date,
        urgency,
      },
      { onSuccess: (req) => navigate(`/request/${req.id}`) },
    )
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">New Request</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Tell us the field, operation and date. The network finds the best machine.
        </p>
      </header>

      <div className="max-w-2xl">
        <Card title="Request details">
          <form onSubmit={onSubmit} className="space-y-4">
            <Row label="Farmer">
              <FarmerPicker value={farmerId} onChange={setFarmerId} label="" />
            </Row>

            <Row label="Field">
              <select
                value={fieldId}
                onChange={(e) => setFieldId(e.target.value)}
                disabled={!farmerId || fieldsQ.isLoading}
                className={selectCls}
              >
                {!farmerId && <option value="">Pick a farmer first</option>}
                {farmerId && fieldsQ.isLoading && <option value="">Loading fields...</option>}
                {farmerId && !fieldsQ.isLoading && fields.length === 0 && (
                  <option value="">No fields for this farmer</option>
                )}
                {fields.map((f) => (
                  <option key={f.id} value={f.id}>
                    #{f.id} · {f.crop_type} ({f.area} acres)
                  </option>
                ))}
              </select>
            </Row>

            <Row label="Operation">
              <select value={operation} onChange={(e) => setOperation(e.target.value)} className={selectCls}>
                {OPERATIONS.map((op) => (
                  <option key={op} value={op}>
                    {op}
                  </option>
                ))}
              </select>
            </Row>

            <Row label="Preferred date">
              <input
                type="date"
                value={date}
                min={TODAY}
                onChange={(e) => setDate(e.target.value)}
                className={selectCls}
              />
            </Row>

            <Row label="Urgency">
              <select value={urgency} onChange={(e) => setUrgency(e.target.value)} className={selectCls}>
                {URGENCIES.map((u) => (
                  <option key={u.value} value={u.value}>
                    {u.label}
                  </option>
                ))}
              </select>
            </Row>

            {create.isError && (
              <ErrorState message={create.error?.message || 'Could not create the request.'} />
            )}

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={!canSubmit}>
                <PlusCircle size={16} />
                {create.isPending ? 'Submitting...' : 'Submit request'}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  )
}

const selectCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 disabled:opacity-60'

function Row({ label, children }) {
  return (
    <div className="grid gap-1.5 sm:grid-cols-[160px_1fr] sm:items-center">
      <label className="text-sm font-medium text-slate-600">{label}</label>
      <div>{children}</div>
    </div>
  )
}
