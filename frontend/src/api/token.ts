// Token storage. The Login screen's "Keep me signed in on this device"
// checkbox (design/Login.html) controls persistence: checked -> localStorage
// (survives closing the browser), unchecked -> sessionStorage (cleared when
// the tab/browser closes). Only one of the two stores is ever written to.

const TOKEN_KEY = 'boneage_ai_token'
const ROLE_KEY = 'boneage_ai_role'

export function saveSession(token: string, role: string, remember: boolean): void {
  const store = remember ? localStorage : sessionStorage
  const other = remember ? sessionStorage : localStorage
  store.setItem(TOKEN_KEY, token)
  store.setItem(ROLE_KEY, role)
  other.removeItem(TOKEN_KEY)
  other.removeItem(ROLE_KEY)
}

export function loadSession(): { token: string; role: string } | null {
  const token = localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY)
  const role = localStorage.getItem(ROLE_KEY) ?? sessionStorage.getItem(ROLE_KEY)
  if (!token || !role) return null
  return { token, role }
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(ROLE_KEY)
}
