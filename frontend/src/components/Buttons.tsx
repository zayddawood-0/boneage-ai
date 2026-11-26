import type { ButtonHTMLAttributes, CSSProperties } from 'react'

export function primaryButtonStyle(height = 44, fontSize = 14): CSSProperties {
  return {
    height,
    padding: '0 18px',
    border: 0,
    borderRadius: 8,
    background: '#24614B',
    color: '#fff',
    fontWeight: 600,
    fontSize,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    textDecoration: 'none',
    boxSizing: 'border-box',
  }
}

export function secondaryButtonStyle(height = 44): CSSProperties {
  return {
    height,
    padding: '0 18px',
    border: '1px solid var(--line)',
    borderRadius: 8,
    background: 'var(--surface)',
    color: 'var(--ink)',
    fontWeight: 600,
    fontSize: 14,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    textDecoration: 'none',
    boxSizing: 'border-box',
  }
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  height?: number
  fontSize?: number
}

export function PrimaryButton({ height = 44, fontSize = 14, style, disabled, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      style={{
        ...primaryButtonStyle(height, fontSize),
        opacity: disabled ? 0.6 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
        ...style,
      }}
      {...rest}
    />
  )
}

export function SecondaryButton({ height = 44, style, disabled, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      style={{
        ...secondaryButtonStyle(height),
        opacity: disabled ? 0.6 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
        ...style,
      }}
      {...rest}
    />
  )
}
