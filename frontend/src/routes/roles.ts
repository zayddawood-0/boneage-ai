import type { Role } from '../api/types'

// Matches docs/requirements.md#user-roles exactly (also enforced
// server-side in backend/app/deps.py) — where each role lands after login,
// and where they're sent if they land on a route they can't access.
export function defaultRouteForRole(role: Role): string {
  switch (role) {
    case 'doctor':
      return '/'
    case 'radiographer':
      return '/analysis/new'
    case 'admin':
      return '/settings'
    default:
      return '/login'
  }
}
