import { useAuth } from '../auth/AuthContext'

const ROLE_LABEL: Record<string, string> = {
  doctor: 'Doctor',
  radiographer: 'Radiographer',
  admin: 'Admin',
}

function initialsFromEmail(email: string): string {
  const local = email.split('@')[0] ?? ''
  const parts = local.split(/[._-]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return local.slice(0, 2).toUpperCase() || '—'
}

// design/*.html shows a hardcoded "[Doctor name]" / "Pediatric endocrinology"
// placeholder here. The backend's login response only returns role (no
// profile name/specialty — see backend/app/schemas.py TokenResponse), so
// this shows the signed-in email and role label instead of inventing a name.
export function UserChip() {
  const { user } = useAuth()
  if (!user) return null

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        background: 'var(--surface)',
        border: '1px solid var(--input)',
        borderRadius: 8,
        padding: '6px 12px 6px 6px',
      }}
    >
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          background: 'var(--avatar)',
          color: 'var(--accent-text)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: 13,
        }}
      >
        {initialsFromEmail(user.email)}
      </div>
      <div style={{ fontSize: 13 }}>
        <div style={{ fontWeight: 600 }}>{user.email}</div>
        <div style={{ color: 'var(--muted)' }}>{ROLE_LABEL[user.role] ?? user.role}</div>
      </div>
    </div>
  )
}
