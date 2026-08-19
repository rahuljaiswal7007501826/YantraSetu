import apiClient from '../lib/apiClient'

export const voiceService = {
  // Upload a short audio clip to the backend proxy (-> Bhashini). We clear the
  // JSON default Content-Type so the browser sets multipart/form-data with the
  // correct boundary; the apiClient interceptor still attaches the bearer token.
  transcribe: (blob, filename = 'clip.webm') => {
    const form = new FormData()
    form.append('audio', blob, filename)
    return apiClient
      .post('/voice/transcribe', form, { headers: { 'Content-Type': undefined } })
      .then((r) => r.data)
  },

  // Ask the backend proxy (-> Bhashini TTS) to speak a Hindi string.
  // Returns { audio_base64, mime, language, cached }.
  speak: (text) => apiClient.post('/voice/speak', { text }).then((r) => r.data),
}
