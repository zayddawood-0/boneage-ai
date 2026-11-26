import type { CSSProperties, ElementType, ReactNode } from 'react'

// The repeated card shell seen on every screen:
// background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 22px
export function Card({
  as: As = 'section',
  style,
  children,
  ...rest
}: {
  as?: ElementType
  style?: CSSProperties
  children: ReactNode
  [key: string]: unknown
}) {
  return (
    <As
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: 22,
        boxSizing: 'border-box',
        ...style,
      }}
      {...rest}
    >
      {children}
    </As>
  )
}
