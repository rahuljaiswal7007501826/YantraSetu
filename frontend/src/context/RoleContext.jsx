import { createContext, useContext, useMemo, useState } from 'react'

// The three demo personas. Keys are stable identifiers; values are labels.
export const ROLES = {
  district_admin: 'District Admin',
  chc_operator: 'CHC Operator',
  farmer: 'Farmer',
}

const RoleContext = createContext(null)

/**
 * RoleProvider - a lightweight stand-in for real authentication.
 *
 * It deliberately exposes an auth-shaped value ({ role, user, isAuthenticated })
 * so a future JWT-backed AuthProvider can replace this component without any
 * page or service having to change: they only ever read `useRole()`.
 */
export function RoleProvider({ children }) {
  const [role, setRole] = useState('district_admin')

  const value = useMemo(
    () => ({
      role,
      setRole,
      user: { name: ROLES[role], role },
      isAuthenticated: true, // always true in the mock; real auth will compute this
    }),
    [role],
  )

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>
}

export function useRole() {
  const ctx = useContext(RoleContext)
  if (!ctx) throw new Error('useRole must be used within a RoleProvider')
  return ctx
}
