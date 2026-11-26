// design/Settings.html switch — on: background #24614B, knob at left:22px;
// off: background var(--line), knob at left:2px.
export function ToggleSwitch({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (checked: boolean) => void
  label: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      style={{
        flex: '0 0 auto',
        position: 'relative',
        width: 44,
        height: 24,
        border: 0,
        borderRadius: 12,
        padding: 0,
        background: checked ? '#24614B' : 'var(--line)',
      }}
    >
      <span
        style={{
          position: 'absolute',
          top: 2,
          left: checked ? 22 : 2,
          width: 20,
          height: 20,
          borderRadius: '50%',
          background: '#fff',
        }}
      />
    </button>
  )
}
