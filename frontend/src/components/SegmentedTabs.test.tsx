import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { SegmentedTabs } from './SegmentedTabs'

const OPTIONS = [
  { key: 'xray' as const, label: 'X-ray' },
  { key: 'overlay' as const, label: 'Heatmap overlay' },
  { key: 'sideBySide' as const, label: 'Side by side' },
]

describe('SegmentedTabs', () => {
  it('renders every option as a real button inside a labelled group', () => {
    render(<SegmentedTabs options={OPTIONS} value="xray" onChange={() => {}} ariaLabel="Image view" />)
    const group = screen.getByRole('group', { name: 'Image view' })
    for (const option of OPTIONS) {
      expect(screen.getByRole('button', { name: option.label })).toBeInTheDocument()
    }
    expect(group).toBeInTheDocument()
  })

  it('marks only the active option as pressed', () => {
    render(<SegmentedTabs options={OPTIONS} value="overlay" onChange={() => {}} ariaLabel="Image view" />)
    expect(screen.getByRole('button', { name: 'X-ray' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: 'Heatmap overlay' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Side by side' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('calls onChange with the clicked option key', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<SegmentedTabs options={OPTIONS} value="xray" onChange={onChange} ariaLabel="Image view" />)
    await user.click(screen.getByRole('button', { name: 'Side by side' }))
    expect(onChange).toHaveBeenCalledWith('sideBySide')
  })

  it('switches the active tab when used as a controlled component', async () => {
    function Controlled() {
      const [value, setValue] = useState<'xray' | 'overlay' | 'sideBySide'>('xray')
      return <SegmentedTabs options={OPTIONS} value={value} onChange={setValue} ariaLabel="Image view" />
    }
    const user = userEvent.setup()
    render(<Controlled />)
    await user.click(screen.getByRole('button', { name: 'Heatmap overlay' }))
    expect(screen.getByRole('button', { name: 'Heatmap overlay' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'X-ray' })).toHaveAttribute('aria-pressed', 'false')
  })
})
