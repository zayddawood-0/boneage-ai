import type { Sex } from '../api/types'

const ON_STYLE = {
  height: 44,
  borderRadius: 8,
  border: '2px solid var(--accent-text)',
  background: 'var(--ok-bg)',
  color: 'var(--ok-text)',
  fontWeight: 600,
  fontSize: 14,
}
const OFF_STYLE = {
  height: 44,
  borderRadius: 8,
  border: '1px solid var(--line)',
  background: 'var(--surface)',
  color: 'var(--text2)',
  fontWeight: 500,
  fontSize: 14,
}

// design/Main.html + design/NewAnalysis.html: "Sex (model input)" two-up grid.
export function SexPicker({
  value,
  onChange,
}: {
  value: Sex | null
  onChange: (sex: Sex) => void
}) {
  return (
    <div
      role="group"
      aria-label="Sex"
      style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}
    >
      <button
        type="button"
        onClick={() => onChange('male')}
        aria-pressed={value === 'male'}
        style={value === 'male' ? ON_STYLE : OFF_STYLE}
      >
        Male
      </button>
      <button
        type="button"
        onClick={() => onChange('female')}
        aria-pressed={value === 'female'}
        style={value === 'female' ? ON_STYLE : OFF_STYLE}
      >
        Female
      </button>
    </div>
  )
}
