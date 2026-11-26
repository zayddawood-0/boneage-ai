import { ToggleSwitch } from './ToggleSwitch'

// design/Settings.html repeated row: title + description on the left, a
// toggle switch on the right, separated by a bottom border.
export function SettingsToggleRow({
  title,
  description,
  checked,
  onChange,
  noBorder = false,
}: {
  title: string
  description: string
  checked: boolean
  onChange: (checked: boolean) => void
  noBorder?: boolean
}) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 16,
        padding: '14px 0',
        borderBottom: noBorder ? undefined : '1px solid var(--row)',
      }}
    >
      <div>
        <div style={{ fontSize: 14, fontWeight: 600 }}>{title}</div>
        <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 2 }}>{description}</div>
      </div>
      <ToggleSwitch checked={checked} onChange={onChange} label={title} />
    </div>
  )
}
