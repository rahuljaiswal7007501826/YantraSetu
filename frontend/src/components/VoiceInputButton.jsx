import { Check, Loader2, Mic, Square, X } from 'lucide-react'

import { useVoiceToText } from '../hooks/useVoiceToText'
import Button from './ui/Button'

/**
 * Mic button that transcribes Hindi speech and hands the (farmer-editable)
 * transcript to `onTranscript`. Never auto-submits and never gates the form -
 * if voice is unavailable it simply disables with a tooltip and typing works.
 */
export default function VoiceInputButton({ onTranscript }) {
  const v = useVoiceToText()

  if (!v.supported) {
    return (
      <button
        type="button"
        disabled
        title="Voice input isn't supported on this browser - please type your request below."
        className="inline-flex cursor-not-allowed items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-400"
      >
        <Mic size={16} /> Voice unavailable
      </button>
    )
  }

  const applyTranscript = () => {
    onTranscript?.(v.transcript)
    v.reset()
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {v.state === 'recording' ? (
          <button
            type="button"
            onClick={v.stopRecording}
            className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-white" />
            </span>
            <Square size={14} /> Stop &amp; transcribe
          </button>
        ) : v.state === 'processing' ? (
          <button
            type="button"
            disabled
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3.5 py-2 text-sm text-slate-500"
          >
            <Loader2 size={16} className="animate-spin" /> Transcribing...
          </button>
        ) : (
          <Button type="button" variant="secondary" onClick={v.startRecording}>
            <Mic size={16} /> Speak your request (Hindi)
          </Button>
        )}
        {v.state !== 'recording' && v.state !== 'processing' && (
          <span className="text-xs text-slate-400">Optional - you can also just type below.</span>
        )}
      </div>

      {v.state === 'preview' && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-3">
          <label className="text-xs font-medium text-slate-600">
            Check and edit what we heard, then fill the form:
          </label>
          <textarea
            value={v.transcript}
            onChange={(e) => v.setTranscript(e.target.value)}
            rows={2}
            dir="auto"
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800"
          />
          <div className="mt-2 flex gap-2">
            <Button type="button" onClick={applyTranscript} disabled={!v.transcript.trim()}>
              <Check size={16} /> Use this
            </Button>
            <Button type="button" variant="ghost" onClick={v.reset}>
              <X size={16} /> Discard
            </Button>
          </div>
        </div>
      )}

      {v.error && <p className="text-xs text-amber-700">{v.error.message}</p>}
    </div>
  )
}
