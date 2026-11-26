import { useEffect, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import * as api from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Role } from '../api/types'
import {
  DashboardIcon,
  LogoMark,
  ModelIcon,
  NewAnalysisIcon,
  PatientsIcon,
  QueueIcon,
  SettingsIcon,
} from './icons'

interface NavItem {
  to: string
  label: string
  icon: typeof DashboardIcon
  roles: Role[]
  badge?: boolean
}

// Visibility matches the permission matrix in docs/requirements.md#user-roles
// exactly (also enforced server-side — see backend/app/deps.py).
const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: DashboardIcon, roles: ['doctor'] },
  { to: '/analysis/new', label: 'New analysis', icon: NewAnalysisIcon, roles: ['doctor', 'radiographer'] },
  { to: '/queue', label: 'Review queue', icon: QueueIcon, roles: ['doctor', 'radiographer'], badge: true },
  { to: '/patients', label: 'Patients', icon: PatientsIcon, roles: ['doctor', 'radiographer'] },
  { to: '/model', label: 'Model performance', icon: ModelIcon, roles: ['doctor', 'admin'] },
  { to: '/settings', label: 'Settings', icon: SettingsIcon, roles: ['admin'] },
]

const linkBaseStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  padding: '11px 12px',
  borderRadius: 8,
  textDecoration: 'none',
  fontSize: 14,
}

function useAwaitingCount(enabled: boolean): number | null {
  const [count, setCount] = useState<number | null>(null)
  const location = useLocation()

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    api
      .listCases({ page_size: 200 })
      .then((response) => {
        if (cancelled) return
        const awaiting = response.cases.filter(
          (c) => (c.flag_status === 'flagged' || c.flag_status === 'needs_review') && c.decision === null,
        ).length
        setCount(awaiting)
      })
      .catch(() => {
        if (!cancelled) setCount(null)
      })
    return () => {
      cancelled = true
    }
    // Re-fetch whenever the route changes, so the badge picks up decisions
    // recorded elsewhere without needing a global store.
  }, [enabled, location.pathname])

  return count
}

export function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const role = user?.role
  const canSeeQueue = role === 'doctor' || role === 'radiographer'
  const awaitingCount = useAwaitingCount(canSeeQueue)

  const handleSignOut = () => {
    logout()
    navigate('/login')
  }

  const items = NAV_ITEMS.filter((item) => (role ? item.roles.includes(role) : false))

  return (
    <nav
      aria-label="Main"
      style={{
        flex: '1 1 220px',
        maxWidth: 260,
        background: '#1C1917',
        color: '#EDE9E3',
        padding: '24px 16px',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        gap: 28,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 8px' }}>
        <LogoMark />
        <div>
          <div style={{ fontWeight: 700, fontSize: 16 }}>BoneAge AI</div>
          <div style={{ fontSize: 12, color: '#B5ADA3' }}>Growth screening</div>
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {items.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              style={({ isActive }) =>
                isActive
                  ? { ...linkBaseStyle, background: '#2E2A25', color: '#fff', fontWeight: 600 }
                  : { ...linkBaseStyle, color: '#D6CFC6' }
              }
            >
              <Icon />
              {item.label}
              {item.badge && awaitingCount !== null && awaitingCount > 0 && (
                <span
                  style={{
                    marginLeft: 'auto',
                    background: '#F2A65A',
                    color: '#1A0E05',
                    fontSize: 12,
                    fontWeight: 700,
                    padding: '1px 8px',
                    borderRadius: 10,
                  }}
                >
                  {awaitingCount}
                </span>
              )}
            </NavLink>
          )
        })}
      </div>
      <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div
          style={{
            background: '#26231F',
            borderRadius: 10,
            padding: 14,
            fontSize: 12,
            lineHeight: 1.5,
            color: '#CFC8BF',
          }}
        >
          <div style={{ fontWeight: 600, color: '#fff', marginBottom: 4 }}>Model</div>
          CNN + sex input · trained on RSNA Bone Age 2017
        </div>
        <button
          type="button"
          onClick={handleSignOut}
          style={{
            color: '#D6CFC6',
            fontSize: 13,
            padding: '8px 12px',
            textDecoration: 'none',
            background: 'transparent',
            border: 0,
            textAlign: 'left',
          }}
        >
          Sign out
        </button>
      </div>
    </nav>
  )
}
