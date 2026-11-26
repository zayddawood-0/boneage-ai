import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

// The root wrapper + <main> shell repeated identically across every
// post-login screen in design/*.html.
export function AppLayout() {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', minHeight: '100vh' }}>
      <Sidebar />
      <main
        style={{
          flex: '999 1 560px',
          minWidth: 0,
          padding: '24px 32px 48px',
          boxSizing: 'border-box',
          display: 'flex',
          flexDirection: 'column',
          gap: 24,
          maxWidth: 1240,
        }}
      >
        <Outlet />
      </main>
    </div>
  )
}
