import { useRef, useState } from 'react'
import { Loader2, Volume2 } from 'lucide-react'

import { voiceService } from '../services/voiceService'

/**
 * Speaker button that reads a Hindi string aloud (Phase 18).
 *
 * Props:
 *   - text:  the on-screen English copy (used for the accessible label)
 *   - hindi: the Hindi string actually spoken (a faithful translation of `text`)
 *
 * Priority is Bhashini TTS (quality matters for farmer trust); on failure it
 * falls back to the browser's speechSynthesis with a Hindi voice if one is
 * installed - best-effort only, since budget Android often lacks a real Hindi
 * voice. The on-screen text is always present, so audio is pure convenience:
 * if everything fails the button just shows an "unavailable" tooltip.
 */
export default function SpeakButton({ text, hindi, className = '' }) {
  const [state, setState] = useState('idle') // idle | loading | playing | error
  const audioRef = useRef(null)

  const spoken = (hindi || text || '').trim()
  const hasBrowserTTS = typeof window !== 'undefined' && 'speechSynthesis' in window

  const stop = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    if (hasBrowserTTS) window.speechSynthesis.cancel()
  }

  const speakViaBrowser = () => {
    if (!hasBrowserTTS) return false
    try {
      const u = new SpeechSynthesisUtterance(spoken)
      u.lang = 'hi-IN'
      const hiVoice = window.speechSynthesis.getVoices().find((v) => v.lang?.toLowerCase().startsWith('hi'))
      if (hiVoice) u.voice = hiVoice
      window.speechSynthesis.cancel()
      window.speechSynthesis.speak(u)
      return true
    } catch {
      return false
    }
  }

  const onClick = async () => {
    if (state === 'loading' || state === 'playing') {
      stop()
      setState('idle')
      return
    }
    if (!spoken) return

    setState('loading')
    try {
      const data = await voiceService.speak(spoken)
      const audio = new Audio(`data:${data.mime || 'audio/wav'};base64,${data.audio_base64}`)
      audioRef.current = audio
      audio.onended = () => setState('idle')
      audio.onerror = () => setState('idle')
      await audio.play()
      setState('playing')
    } catch {
      // Bhashini/proxy failed -> best-effort browser speech, else show error.
      if (speakViaBrowser()) setState('idle')
      else setState('error')
    }
  }

  const label = text ? `Read aloud (Hindi): ${text}` : 'Read aloud in Hindi'
  const Icon = state === 'loading' ? Loader2 : Volume2

  return (
    <button
      type="button"
      onClick={onClick}
      title={state === 'error' ? 'Audio unavailable right now - the text shown is the same.' : label}
      aria-label={label}
      className={`inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 ${className}`}
    >
      <Icon size={14} className={state === 'loading' ? 'animate-spin' : ''} />
      {state === 'playing' ? 'रोकें' : 'सुनें'}
    </button>
  )
}
