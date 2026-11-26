import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import type { Role } from '../api/types'
import { defaultRouteForRole } from './roles'

export function RequireRole({ roles }: { roles: Role[] }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />

  if (!roles.includes(user.role)) {
    return <Navigate to={defaultRouteForRole(user.role)} replace />
  }
  return <Outlet />
}
