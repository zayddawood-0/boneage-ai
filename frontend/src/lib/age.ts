// Age/gap formatting matching design/*.html exactly: "9y 2m", gaps as
// "+2y 5m" / "−0y 7m" (note: that's U+2212 MINUS SIGN, not a hyphen).

const MINUS_SIGN = '−'

export function formatAgeMonths(totalMonths: number | null | undefined): string {
  if (totalMonths == null || Number.isNaN(totalMonths)) return '—'
  const abs = Math.round(Math.abs(totalMonths))
  const years = Math.floor(abs / 12)
  const months = abs % 12
  return `${years}y ${months}m`
}

export function formatGapMonths(gapMonths: number | null | undefined): string {
  if (gapMonths == null || Number.isNaN(gapMonths)) return '—'
  const rounded = Math.round(gapMonths)
  const sign = rounded < 0 ? MINUS_SIGN : '+'
  return `${sign}${formatAgeMonths(rounded)}`
}

export function formatDateDisplay(isoDate: string | null | undefined): string {
  if (!isoDate) return '—'
  const date = new Date(`${isoDate}T00:00:00`)
  if (Number.isNaN(date.getTime())) return isoDate
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(
    date,
  )
}

/** Parses a free-text age reading ("9y 0m", "9 0", or a plain number of
 * months) into total months — the backend's manual_bone_age_months field
 * is numeric, but design/Case.html's input is a free-text field (placeholder
 * "e.g. 9y 0m"), so this bridges the two without changing the visible field. */
export function parseAgeInputToMonths(text: string): number | null {
  const trimmed = text.trim()
  if (!trimmed) return null

  const ym = trimmed.match(/^(\d+)\s*y\s*(\d+)\s*m$/i)
  if (ym) return Number(ym[1]) * 12 + Number(ym[2])

  const yOnly = trimmed.match(/^(\d+)\s*y$/i)
  if (yOnly) return Number(yOnly[1]) * 12

  const twoNumbers = trimmed.match(/^(\d+)\s+(\d+)$/)
  if (twoNumbers) return Number(twoNumbers[1]) * 12 + Number(twoNumbers[2])

  const plainMonths = trimmed.match(/^(\d+)\s*m?$/i)
  if (plainMonths) return Number(plainMonths[1])

  return null
}

/** Mirrors backend/app/agent/tools.py::compute_chronological_age_months — used
 * only for a live preview before a case exists; the backend value is authoritative. */
export function computeChronologicalAgeMonths(
  dateOfBirth: string | null | undefined,
  xrayDate: string | null | undefined,
): number | null {
  if (!dateOfBirth || !xrayDate) return null
  const dob = new Date(`${dateOfBirth}T00:00:00`)
  const xray = new Date(`${xrayDate}T00:00:00`)
  if (Number.isNaN(dob.getTime()) || Number.isNaN(xray.getTime())) return null

  let months = (xray.getFullYear() - dob.getFullYear()) * 12 + (xray.getMonth() - dob.getMonth())
  if (xray.getDate() < dob.getDate()) {
    months -= 1
  }
  return Math.max(months, 0)
}
