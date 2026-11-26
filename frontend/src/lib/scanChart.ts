// Builds point coordinates for the "Previous scans" line chart in
// design/Case.html — same viewBox/axis style, but computed from real scan
// data instead of 3 hardcoded points.
export interface ScanPoint {
  dateLabel: string
  chronMonths: number
  boneMonths: number
}

export interface PlottedScan {
  dateLabel: string
  x: number
  chronY: number
  boneY: number
}

const VIEW = { left: 40, right: 450, top: 20, bottom: 190 }

export function plotScans(points: ScanPoint[]): PlottedScan[] {
  if (points.length === 0) return []

  const allMonths = points.flatMap((p) => [p.chronMonths, p.boneMonths])
  const minMonths = Math.min(...allMonths)
  const maxMonths = Math.max(...allMonths)
  const span = Math.max(maxMonths - minMonths, 1)

  const toY = (months: number) => VIEW.bottom - ((months - minMonths) / span) * (VIEW.bottom - VIEW.top)

  const xStep = points.length > 1 ? (VIEW.right - VIEW.left) / (points.length - 1) : 0

  return points.map((point, index) => ({
    dateLabel: point.dateLabel,
    x: points.length > 1 ? VIEW.left + xStep * index : (VIEW.left + VIEW.right) / 2,
    chronY: toY(point.chronMonths),
    boneY: toY(point.boneMonths),
  }))
}

export const SCAN_CHART_VIEW = VIEW
