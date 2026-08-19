import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { clearToken, getToken, setToken } from '../lib/authToken'
import { authService } from '../services/authService'

// Frontend persona keys -> display labels. Pages and the sidebar switch on the
// KEY, so these keys are the app's stable role vocabulary.
export const ROLES = {
  district_admin: 'District Admin',
  chc_operator: 'CHC Manager',
  operator: 'Machine Operator',
  farmer: 'Farmer',
}

// Backend UserRole (from the JWT / auth/me) -> frontend persona key.
const BACKEND_TO_FRONTEND = {
  ADMIN: 'district_admin',
  CHC_MANAGER: 'chc_operator',
  OPERATOR: 'operator',
  FARMER: 'farmer',
}

// Where each persona lands after login (and when hitting "/" via the menu).
export const LANDING_BY_ROLE = {
  district_admin: '/',
  chc_operator: '/relocations',
  operator: '/network',
  farmer: '/my-requests',
}

const RoleContext = createContext(null)

function toFrontendUser(apiUser) {
  return {
    id: apiUser.id,
    name: apiUser.name,
    email: apiUser.email,
    role: BACKEND_TO_FRONTEND[apiUser.role] ?? 'farmer', // pages/nav read this
    backendRole: apiUser.role,
    farmerId: apiUser.farmer_id ?? null,
  }
}

/**
 * RoleProvider - real JWT-backed auth.
 *
 * It keeps the exact value shape the mock exposed ({ role, user, isAuthenticated })
 * plus { loading, login, logout }, so existing pages/services that only read
 * useRole() keep working unchanged.
 */
export function RoleProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  // On first load: if a token exists, validate it via /auth/me.
  useEffect(() => {
    let cancelled = false
    async function bootstrap() {
      if (!getToken()) {
        setLoading(false)
        return
      }
      try {
        const me = await authService.me()
        if (!cancelled) setUser(toFrontendUser(me))
      } catch {
        if (!cancelled) {
          clearToken()
          setUser(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    bootstrap()
    return () => {
      cancelled = true
    }
  }, [])

  // apiClient fires this after any 401 (expired/invalid token) so we log out.
  useEffect(() => {
    const onUnauthorized = () => setUser(null)
    window.addEventListener('auth:unauthorized', onUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', onUnauthorized)
  }, [])

  const login = useCallback(async (email, password) => {
    const { access_token: accessToken } = await authService.login(email, password)
    setToken(accessToken)
    const me = await authService.me()
    const fe = toFrontendUser(me)
    setUser(fe)
    return fe
  }, [])

  const value = useMemo(
    () => ({
      user,
      role: user?.role ?? null,
      isAuthenticated: !!user,
      loading,
      login,
      logout,
    }),
    [user, loading, login, logout],
  )

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>
}

export function useRole() {
  const ctx = useContext(RoleContext)
  if (!ctx) throw new Error('useRole must be used within a RoleProvider')
  return ctx
}
