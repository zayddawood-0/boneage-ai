import type { ReactNode } from 'react'
import { SecondaryButton } from './Buttons'
import { StatusChip } from './StatusChip'

// Approved addition (task: "loading, empty and error states for every API
// call, using the existing card and chip styles") — design/ doesn't draw
// these explicitly, so they reuse the same tokens/typography as everything
// else rather than introducing new visual language.

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div role="status" style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--muted)', fontSize: 14 }}>
      {label}
    </div>
  )
}

export function EmptyState({ title, description }: { title: string; description?: ReactNode }) {
  return (
    <div style={{ padding: '32px 16px', textAlign: 'center' }}>
      <div style={{ fontWeight: 600, fontSize: 15 }}>{title}</div>
      {description && <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 6 }}>{description}</div>}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" style={{ padding: '24px 16px', textAlign: 'center' }}>
      <StatusChip variant="flag">Error</StatusChip>
      <div style={{ marginTop: 10, fontSize: 14 }}>{message}</div>
      {onRetry && (
        <div style={{ marginTop: 12 }}>
          <SecondaryButton onClick={onRetry}>Try again</SecondaryButton>
        </div>
      )}
    </div>
  )
}
