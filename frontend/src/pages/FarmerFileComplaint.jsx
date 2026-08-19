import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send } from 'lucide-react'

import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import ErrorState from '../components/states/ErrorState'
import SpeakButton from '../components/SpeakButton'
import VoiceInputButton from '../components/VoiceInputButton'
import { hiStrings } from '../i18n/hi-strings'
import { useCreateComplaint } from '../hooks/useComplaints'
import { useRequests } from '../hooks/useRequests'

const CATEGORIES = [
  { value: 'machine_no_show', label: 'Machine did not show up' },
  { value: 'machine_breakdown', label: 'Machine breakdown' },
  { value: 'wrong_machine_type', label: 'Wrong machine type' },
  { value: 'operator_conduct', label: 'Operator conduct' },
  { value: 'chc_service', label: 'CHC service' },
  { value: 'other', label: 'Other' },
]

const COMPLAINT_INSTRUCTIONS_EN =
  'File your complaint here. Pick a category and write the details, or press the mic button to speak.'

const selectCls =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 disabled:opacity-60'

export default function FarmerFileComplaint() {
  const navigate = useNavigate()
  const [category, setCategory] = useState(CATEGORIES[0].value)
  const [requestId, setRequestId] = useState('')
  const [description, setDescription] = useState('')

  // The farmer's own requests (backend owner-scopes FARMER) for the optional link.
  const myRequestsQ = useRequests({ limit: 200 })
  const myRequests = myRequestsQ.data ?? []

  const create = useCreateComplaint()
  const canSubmit = Boolean(category && description.trim()) && !create.isPending

  // Voice fills the description (append, never auto-submit).
  const handleVoiceTranscript = (text) => {
    const t = (text || '').trim()
    if (!t) return
    setDescription((prev) => (prev.trim() ? `${prev.trim()} ${t}` : t))
  }

  const onSubmit = (e) => {
    e.preventDefault()
    if (!canSubmit) return
    create.mutate(
      {
        category,
        description: description.trim(),
        demand_request_id: requestId ? Number(requestId) : null,
      },
      { onSuccess: () => navigate('/my-complaints') },
    )
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">File a Complaint</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Tell us what went wrong. Staff will review and respond.
        </p>
      </header>

      <div className="max-w-2xl">
        <Card title="Complaint details">
          <div className="mb-4 flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-500">{COMPLAINT_INSTRUCTIONS_EN}</p>
            <SpeakButton text={COMPLAINT_INSTRUCTIONS_EN} hindi={hiStrings.complaintInstructions} />
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <Row label="Category">
              <select value={category} onChange={(e) => setCategory(e.target.value)} className={selectCls}>
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </Row>

            <Row label="Related request">
              <select
                value={requestId}
                onChange={(e) => setRequestId(e.target.value)}
                className={selectCls}
                disabled={myRequestsQ.isLoading}
              >
                <option value="">None (general complaint)</option>
                {myRequests.map((r) => (
                  <option key={r.id} value={r.id}>
                    #{r.id} · {r.operation_type} ({r.requested_date})
                  </option>
                ))}
              </select>
            </Row>

            <Row label="Description">
              <div className="space-y-2">
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={5}
                  dir="auto"
                  placeholder="Describe the problem..."
                  className={selectCls}
                />
                <VoiceInputButton onTranscript={handleVoiceTranscript} />
              </div>
            </Row>

            {create.isError && (
              <ErrorState message={create.error?.message || 'Could not file the complaint.'} />
            )}

            <div className="flex justify-end pt-2">
              <Button type="submit" disabled={!canSubmit}>
                <Send size={16} />
                {create.isPending ? 'Filing...' : 'File complaint'}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  )
}

function Row({ label, children }) {
  return (
    <div className="grid gap-1.5 sm:grid-cols-[160px_1fr] sm:items-start">
      <label className="pt-2 text-sm font-medium text-slate-600">{label}</label>
      <div>{children}</div>
    </div>
  )
}
