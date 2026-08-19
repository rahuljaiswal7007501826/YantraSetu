import { useRef, useState } from 'react'

import { voiceService } from '../services/voiceService'

/**
 * Voice-to-text with a graceful fallback chain (Phase 17):
 *   1. Record with MediaRecorder, upload to the backend proxy (-> Bhashini).
 *   2. If that fails and the browser has Web Speech API, switch to it on retry.
 *   3. If neither is available, `supported` is false (the button disables).
 *
 * The transcript is never auto-applied - the component shows it for the farmer
 * to edit/confirm first. Browser audio paths can only be verified on a real
 * device/browser; this environment cannot exercise them.
 */
export function useVoiceToText() {
  const [state, setState] = useState('idle') // idle | recording | processing | preview | error
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState(null) // { code, message } | null

  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const recognitionRef = useRef(null)
  const preferWebSpeechRef = useRef(false)

  const hasMediaRecorder =
    typeof window !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof window.MediaRecorder !== 'undefined'
  const SpeechRecognitionImpl =
    typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
  const hasWebSpeech = Boolean(SpeechRecognitionImpl)
  const supported = hasMediaRecorder || hasWebSpeech

  const fail = (code, message) => {
    setError({ code, message })
    setState('error')
  }

  const startWebSpeech = () => {
    try {
      const rec = new SpeechRecognitionImpl()
      rec.lang = 'hi-IN'
      rec.interimResults = false
      rec.maxAlternatives = 1
      rec.onresult = (e) => {
        setTranscript((e.results?.[0]?.[0]?.transcript || '').trim())
        setState('preview')
      }
      rec.onerror = (e) =>
        fail(
          'webspeech_error',
          e.error === 'not-allowed'
            ? 'Microphone permission is blocked. You can type your request below.'
            : 'Speech recognition failed. Please type your request below.',
        )
      rec.onend = () => setState((s) => (s === 'recording' ? 'idle' : s))
      recognitionRef.current = rec
      setError(null)
      setTranscript('')
      setState('recording')
      rec.start()
    } catch {
      fail('webspeech_start_failed', 'Could not start speech recognition. Please type below.')
    }
  }

  const uploadBlob = async (blob) => {
    setState('processing')
    try {
      const ext = blob.type.includes('ogg') ? 'ogg' : blob.type.includes('wav') ? 'wav' : 'webm'
      const data = await voiceService.transcribe(blob, `clip.${ext}`)
      setTranscript((data.transcript || '').trim())
      setState('preview')
    } catch (e) {
      // Proxy/Bhashini failed. Fall back to the browser recognizer on the next tap.
      if (hasWebSpeech) {
        preferWebSpeechRef.current = true
        fail(
          'bhashini_unavailable',
          "Voice service unavailable. Tap the mic again to use your browser's recognizer, or type below.",
        )
      } else {
        fail(
          e?.message ? 'transcribe_failed' : 'transcribe_failed',
          'Could not transcribe the audio. Please type your request below.',
        )
      }
    }
  }

  const startRecording = async () => {
    if (preferWebSpeechRef.current && hasWebSpeech) return startWebSpeech()

    if (hasMediaRecorder) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        const recorder = new MediaRecorder(stream)
        chunksRef.current = []
        recorder.ondataavailable = (e) => {
          if (e.data && e.data.size) chunksRef.current.push(e.data)
        }
        recorder.onstop = () => {
          stream.getTracks().forEach((t) => t.stop())
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
          uploadBlob(blob)
        }
        recorderRef.current = recorder
        setError(null)
        setTranscript('')
        setState('recording')
        recorder.start()
      } catch {
        // Mic blocked/unavailable. Try the browser recognizer, else disable.
        if (hasWebSpeech) {
          preferWebSpeechRef.current = true
          startWebSpeech()
        } else {
          fail('mic_denied', 'Microphone permission is blocked. You can type your request below.')
        }
      }
    } else if (hasWebSpeech) {
      startWebSpeech()
    } else {
      fail('unsupported', 'Voice input is not supported on this browser.')
    }
  }

  const stopRecording = () => {
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop()
    } else if (recognitionRef.current) {
      recognitionRef.current.stop()
    }
  }

  const reset = () => {
    setState('idle')
    setTranscript('')
    setError(null)
  }

  return { supported, state, transcript, setTranscript, error, startRecording, stopRecording, reset }
}
