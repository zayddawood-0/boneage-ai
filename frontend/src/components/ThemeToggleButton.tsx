import { useTheme } from '../theme/ThemeContext'
import { MoonIcon, SunIcon } from './icons'

// design/*.html: every screen's header has this exact button. Icon shown is
// the CURRENT theme's icon (moon while dark, sun while light); the label is
// what clicking it switches TO ("Light" while dark, "Dark" while light) —
// reproduced exactly as drawn, not "fixed".
export function ThemeToggleButton() {
  const { resolvedTheme, toggleTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const label = isDark ? 'Switch to light theme' : 'Switch to dark theme'
  const buttonText = isDark ? 'Light' : 'Dark'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      style={{
        height: 44,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '0 14px',
        border: '1px solid var(--input)',
        borderRadius: 8,
        background: 'var(--surface)',
        color: 'var(--ink)',
        fontSize: 14,
        fontWeight: 600,
      }}
    >
      {isDark ? <MoonIcon /> : <SunIcon />}
      {buttonText}
    </button>
  )
}
