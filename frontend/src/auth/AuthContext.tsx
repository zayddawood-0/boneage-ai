import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import * as api from '../api/client'
import { clearSession, loadSession, saveSession } from '../api/token'
import type { Role } from '../api/types'

interface AuthUser {
  email: string
  role: Role
}

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string, remember: boolean) => Promise<Role>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  // Starts true so a hard reload/deep link (e.g. /queue) doesn't render
  // RequireAuth's "not signed in" redirect before the session below has had
  // a chance to load — see LoginPage's own redirect-when-authenticated,
  // which would otherwise send a deep link straight to the default route.
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const session = loadSession()
    if (session) {
      // The email isn't persisted by the backend's token response, only role —
      // re-derive a display identity from what we do have (see UserChip).
      setUser({ email: sessionStorage.getItem('boneage_ai_email') ?? localStorage.getItem('boneage_ai_email') ?? '', role: session.role as Role })
    }
    setIsLoading(false)
  }, [])

  useEffect(() => {
    api.setUnauthorizedHandler(() => setUser(null))
    return () => api.setUnauthorizedHandler(null)
  }, [])

  const login = useCallback(async (email: string, password: string, remember: boolean): Promise<Role> => {
    const response = await api.login(email, password)
    saveSession(response.token, response.role, remember)
    const store = remember ? localStorage : sessionStorage
    store.setItem('boneage_ai_email', email)
    setUser({ email, role: response.role })
    return response.role
  }, [])

  const logout = useCallback(() => {
    clearSession()
    localStorage.removeItem('boneage_ai_email')
    sessionStorage.removeItem('boneage_ai_email')
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, isAuthenticated: user !== null, isLoading, login, logout }),
    [user, isLoading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
