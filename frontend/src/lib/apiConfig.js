// Central backend base URL for the whole frontend.
//
// - Local dev: leave VITE_API_URL UNSET. API_URL becomes '' so requests use
//   relative paths ('/api', '/health') and Vite's dev proxy forwards them to
//   the backend on http://127.0.0.1:8000 - exactly as before.
// - Production: set VITE_API_URL to the deployed backend origin (no trailing
//   slash), e.g. https://yantrasetu-api.onrender.com
//
// Trailing slashes are trimmed so we never build a double-slash URL.
export const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')
