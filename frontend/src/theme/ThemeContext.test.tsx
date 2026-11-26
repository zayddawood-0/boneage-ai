import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { ThemeToggleButton } from '../components/ThemeToggleButton'
import { ThemeProvider, useTheme } from './ThemeContext'

const STORAGE_KEY = 'boneage_ai_theme_preference'

function Harness() {
  const { preference, resolvedTheme, setPreference } = useTheme()
  return (
    <div>
      <span data-testid="preference">{preference}</span>
      <span data-testid="resolved">{resolvedTheme}</span>
      <ThemeToggleButton />
      <button onClick={() => setPreference('system')}>Match my device</button>
    </div>
  )
}

function renderWithProvider() {
  return render(
    <ThemeProvider>
      <Harness />
    </ThemeProvider>,
  )
}

beforeEach(() => {
  localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})

afterEach(() => {
  localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})

describe('theme toggle', () => {
  it('defaults to light and stamps data-theme on the document root', () => {
    renderWithProvider()
    expect(screen.getByTestId('resolved')).toHaveTextContent('light')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('flips to dark on click, updates the button label, and persists the choice to localStorage', async () => {
    renderWithProvider()
    const user = userEvent.setup()
    const button = screen.getByRole('button', { name: 'Switch to dark theme' })
    await user.click(button)

    expect(screen.getByTestId('resolved')).toHaveTextContent('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    expect(screen.getByRole('button', { name: 'Switch to light theme' })).toBeInTheDocument()
    expect(localStorage.getItem(STORAGE_KEY)).toBe('dark')
  })

  it('restores a previously saved preference on mount', () => {
    localStorage.setItem(STORAGE_KEY, 'dark')
    renderWithProvider()
    expect(screen.getByTestId('resolved')).toHaveTextContent('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })

  it('lets Settings-style "Match my device" selection set the system preference', async () => {
    const user = userEvent.setup()
    renderWithProvider()
    await user.click(screen.getByRole('button', { name: 'Match my device' }))
    expect(screen.getByTestId('preference')).toHaveTextContent('system')
    expect(localStorage.getItem(STORAGE_KEY)).toBe('system')
  })
})
