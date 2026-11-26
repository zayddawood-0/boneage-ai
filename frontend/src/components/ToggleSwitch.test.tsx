import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ToggleSwitch } from './ToggleSwitch'

describe('ToggleSwitch', () => {
  it('exposes itself as a real switch with the correct checked state', () => {
    render(<ToggleSwitch checked={false} onChange={() => {}} label="Auto-clear normal cases" />)
    const switchEl = screen.getByRole('switch', { name: 'Auto-clear normal cases' })
    expect(switchEl).toHaveAttribute('aria-checked', 'false')
  })

  it('reflects checked=true in aria-checked', () => {
    render(<ToggleSwitch checked onChange={() => {}} label="Write a note for the doctor" />)
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'true')
  })

  it('calls onChange with the flipped value on click, and is keyboard operable', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<ToggleSwitch checked={false} onChange={onChange} label="Email me about new flags" />)

    const switchEl = screen.getByRole('switch')
    await user.click(switchEl)
    expect(onChange).toHaveBeenCalledWith(true)

    switchEl.focus()
    await user.keyboard('{Enter}')
    expect(onChange).toHaveBeenCalledTimes(2)
    expect(onChange).toHaveBeenLastCalledWith(true)
  })
})
