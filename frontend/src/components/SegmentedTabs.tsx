export interface SegmentedOption<T extends string> {
  key: T
  label: string
}

// Two sizes seen in design/*.html: the Queue status tabs (height 36, radius
// 7, padding 0 14px) and the image-view switch (height 32, radius 6, padding
// 0 12px). Both share the same "pill-group on a --seg track" structure.
export function SegmentedTabs<T extends string>({
  options,
  value,
  onChange,
  size = 'tabs',
  ariaLabel,
}: {
  options: SegmentedOption<T>[]
  value: T
  onChange: (value: T) => void
  size?: 'tabs' | 'imageView'
  ariaLabel: string
}) {
  const trackRadius = size === 'tabs' ? 10 : 8
  const buttonHeight = size === 'tabs' ? 36 : 32
  const buttonPadding = size === 'tabs' ? '0 14px' : '0 12px'
  const buttonRadius = size === 'tabs' ? 7 : 6
  const gap = size === 'tabs' ? 6 : 4

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap,
        background: 'var(--seg)',
        padding: 4,
        borderRadius: trackRadius,
      }}
    >
      {options.map((option) => {
        const active = option.key === value
        return (
          <button
            key={option.key}
            type="button"
            onClick={() => onChange(option.key)}
            aria-pressed={active}
            style={{
              height: buttonHeight,
              padding: buttonPadding,
              border: 0,
              borderRadius: buttonRadius,
              background: active ? 'var(--surface)' : 'transparent',
              color: active ? 'var(--ink)' : 'var(--muted)',
              fontWeight: active ? 600 : 500,
              fontSize: 13,
            }}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
