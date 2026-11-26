import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { ApiError } from '../api/client'
import { primaryButtonStyle } from '../components/Buttons'
import { LogoMark } from '../components/icons'
import { ThemeToggleButton } from '../components/ThemeToggleButton'
import { defaultRouteForRole } from '../routes/roles'

const inputStyle: React.CSSProperties = {
  height: 44,
  border: '1px solid var(--input)',
  borderRadius: 8,
  padding: '0 12px',
  fontFamily: 'inherit',
  fontSize: 14,
  background: 'var(--surface)',
  color: 'var(--ink)',
  boxSizing: 'border-box',
  width: '100%',
}

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (user) {
    return <Navigate to={defaultRouteForRole(user.role)} replace />
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const role = await login(email, password, remember)
      const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname
      navigate(from ?? defaultRouteForRole(role), { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', minHeight: '100vh' }}>
      <div
        style={{
          flex: '1 1 420px',
          background: '#1C1917',
          color: '#EDE9E3',
          padding: 56,
          boxSizing: 'border-box',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          gap: 40,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <LogoMark size={40} />
          <span style={{ fontWeight: 700, fontSize: 20 }}>BoneAge AI</span>
        </div>
        <div style={{ maxWidth: 460 }}>
          <h1 style={{ margin: 0, fontSize: 40, lineHeight: 1.15, fontWeight: 700 }}>
            Bone age from a hand X-ray, checked against real age.
          </h1>
          <p style={{ margin: '18px 0 0', fontSize: 16, lineHeight: 1.6, color: '#CFC8BF' }}>
            A CNN estimates bone age using the child&apos;s sex as an extra input. When the gap to
            chronological age falls outside the normal range, an agent flags the case for a doctor
            to review.
          </p>
        </div>
        <p style={{ margin: 0, fontSize: 13, color: '#B5ADA3' }}>Decision support only. Not a diagnosis.</p>
      </div>
      <div
        style={{
          flex: '1 1 420px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '48px 24px',
          boxSizing: 'border-box',
          position: 'relative',
        }}
      >
        <div style={{ position: 'absolute', top: 24, right: 24 }}>
          <ThemeToggleButton />
        </div>
        <form
          onSubmit={handleSubmit}
          style={{ width: '100%', maxWidth: 380, display: 'flex', flexDirection: 'column', gap: 18 }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: 26 }}>Sign in</h2>
            <p style={{ margin: '6px 0 0', fontSize: 14, color: 'var(--muted)' }}>
              For doctors and clinical staff
            </p>
          </div>

          {error && (
            <div
              role="alert"
              style={{
                background: 'var(--flag-bg)',
                color: 'var(--flag-text)',
                borderRadius: 8,
                padding: '10px 12px',
                fontSize: 13,
              }}
            >
              {error}
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label htmlFor="email" style={{ fontSize: 13, fontWeight: 600 }}>
              Email
            </label>
            <input
              id="email"
              type="email"
              placeholder="name@hospital.org"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoComplete="username"
              style={inputStyle}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <label htmlFor="pw" style={{ fontSize: 13, fontWeight: 600 }}>
                Password
              </label>
              <a href="#forgot" style={{ fontSize: 13, color: 'var(--accent-text)' }}>
                Forgot password?
              </a>
            </div>
            <input
              id="pw"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              autoComplete="current-password"
              style={inputStyle}
            />
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14 }}>
            <input
              type="checkbox"
              checked={remember}
              onChange={(event) => setRemember(event.target.checked)}
              style={{ width: 18, height: 18 }}
            />
            Keep me signed in on this device
          </label>
          <button type="submit" disabled={loading} style={{ ...primaryButtonStyle(48, 14), opacity: loading ? 0.7 : 1 }}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)', textAlign: 'center' }}>
            No account? Ask your hospital admin for access.
          </p>
        </form>
      </div>
    </div>
  )
}
