import type { ReactNode } from 'react'

// design/*.html status pill styles. Status is never colour-only — every
// variant always renders with its text label (docs/design.md accessibility
// rules), never just a coloured dot.
export type ChipVariant = 'flag' | 'ok' | 'waiting' | 'demo'

const VARIANT_STYLE: Record<ChipVariant, { background: string; color: string }> = {
  flag: { background: 'var(--flag-bg)', color: 'var(--flag-text)' },
  ok: { background: 'var(--ok-bg)', color: 'var(--ok-text)' },
  waiting: { background: 'var(--seg)', color: 'var(--text2)' },
  // Approved addition (not in design/): amber "Demo model" chip, reusing the
  // flag chip's exact style, for prediction_source === "mock" results.
  demo: { background: 'var(--flag-bg)', color: 'var(--flag-text)' },
}

export function StatusChip({
  variant,
  size = 'sm',
  children,
}: {
  variant: ChipVariant
  size?: 'sm' | 'md'
  children: ReactNode
}) {
  const colours = VARIANT_STYLE[variant]
  const sizing =
    size === 'md' ? { fontSize: 13, padding: '6px 12px' } : { fontSize: 12, padding: '4px 10px' }
  return (
    <span
      style={{
        ...colours,
        ...sizing,
        fontWeight: 600,
        borderRadius: 999,
        display: 'inline-block',
      }}
    >
      {children}
    </span>
  )
}

/** Maps a case's flag_status/gap_direction to the chip variant + label used
 * throughout design/ ("Delayed" / "Advanced" / "Normal"). */
export function flagChipProps(
  flagStatus: string | null | undefined,
  gapDirection: string | null | undefined,
): { variant: ChipVariant; label: string } {
  if (flagStatus === 'flagged') {
    if (gapDirection === 'delayed') return { variant: 'flag', label: 'Delayed' }
    if (gapDirection === 'advanced') return { variant: 'flag', label: 'Advanced' }
    return { variant: 'flag', label: 'Flagged' }
  }
  if (flagStatus === 'needs_review' || gapDirection === 'uncertain') {
    return { variant: 'flag', label: 'Uncertain' }
  }
  return { variant: 'ok', label: 'Normal' }
}
