// JWT storage for the MVP/SIH build.
//
// NOTE: localStorage is an intentional MVP trade-off - it's simple and survives
// reloads, but it is readable by JavaScript (so vulnerable to XSS). A future
// hardening step would move to httpOnly refresh cookies. This is documented and
// acceptable for the demo; it is not a blocker.
const TOKEN_KEY = 'yantrasetu_token'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    /* ignore (e.g. private mode) */
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* ignore */
  }
}
