import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { StatusChip, flagChipProps } from './StatusChip'

describe('StatusChip', () => {
  it('renders its label as visible text, not colour-only', () => {
    render(<StatusChip variant="flag">Delayed</StatusChip>)
    expect(screen.getByText('Delayed')).toBeInTheDocument()
  })

  it('renders the demo chip with the same style as the flag chip', () => {
    render(
      <>
        <StatusChip variant="flag">Flag</StatusChip>
        <StatusChip variant="demo">Demo model</StatusChip>
      </>,
    )
    const flag = screen.getByText('Flag')
    const demo = screen.getByText('Demo model')
    expect(demo.style.background).toBe(flag.style.background)
    expect(demo.style.color).toBe(flag.style.color)
  })
})

describe('flagChipProps', () => {
  it('maps a flagged+delayed case to the flag variant', () => {
    expect(flagChipProps('flagged', 'delayed')).toEqual({ variant: 'flag', label: 'Delayed' })
  })

  it('maps a flagged+advanced case to the flag variant', () => {
    expect(flagChipProps('flagged', 'advanced')).toEqual({ variant: 'flag', label: 'Advanced' })
  })

  it('maps needs_review to an uncertain flag', () => {
    expect(flagChipProps('needs_review', null)).toEqual({ variant: 'flag', label: 'Uncertain' })
  })

  it('maps a cleared case to the ok variant', () => {
    expect(flagChipProps('cleared', 'within_range')).toEqual({ variant: 'ok', label: 'Normal' })
  })

  it('defaults to normal when flag status is missing', () => {
    expect(flagChipProps(null, null)).toEqual({ variant: 'ok', label: 'Normal' })
  })
})
