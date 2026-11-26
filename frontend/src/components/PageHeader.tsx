import type { ReactNode } from 'react'
import { ThemeToggleButton } from './ThemeToggleButton'
import { UserChip } from './UserChip'

// The <h1> + description + (theme toggle, user chip, [optional extra])
// header repeated on every post-login screen.
export function PageHeader({
  title,
  description,
  extra,
}: {
  title: string
  description: string
  extra?: ReactNode
}) {
  return (
    <header
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 16,
        justifyContent: 'space-between',
      }}
    >
      <div>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700 }}>{title}</h1>
        <p style={{ margin: '4px 0 0', fontSize: 14, color: 'var(--muted)' }}>{description}</p>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12 }}>
        {extra}
        <ThemeToggleButton />
        <UserChip />
      </div>
    </header>
  )
}
