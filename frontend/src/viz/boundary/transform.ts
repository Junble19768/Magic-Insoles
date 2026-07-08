import type { FootSide } from '@/viz/boundary/types'
import type { CopPoint } from '@/types'

/**
 * Map original sensor field (height × width) to display buffer for pyqtgraph-style
 * layout: display index = plotX * displayHeight + plotY, shape (width × height).
 */
export function transformFieldForDisplay(
  field: Float32Array,
  canvasWidth: number,
  canvasHeight: number,
  side: FootSide,
): { field: Float32Array; displayWidth: number; displayHeight: number } {
  const displayWidth = canvasWidth
  const displayHeight = canvasHeight
  const out = new Float32Array(displayWidth * displayHeight)

  for (let row = 0; row < canvasHeight; row += 1) {
    for (let col = 0; col < canvasWidth; col += 1) {
      const value = field[row * canvasWidth + col]
      let plotX = col
      if (side === 'left') {
        plotX = canvasWidth - 1 - col
      }
      const plotY = row
      out[plotY * displayWidth + plotX] = value
    }
  }

  return { field: out, displayWidth, displayHeight }
}

/** Mirror X for left-foot COP in plot coordinates (align heatmap.py). */
export function leftFootMirrorX(canvasWidth: number): number {
  return canvasWidth - 1
}

export function copToDisplayCoords(
  cx: number,
  cy: number,
  side: FootSide,
  canvasWidth: number,
): { x: number; y: number } {
  if (side === 'left') {
    return { x: leftFootMirrorX(canvasWidth) - cx, y: cy }
  }
  return { x: cx, y: cy }
}

export function copPlotToPixelIndex(
  plotX: number,
  plotY: number,
  displayWidth: number,
): number {
  return Math.round(plotY) * displayWidth + Math.round(plotX)
}

/** Map sensor-centroid (cx, cy) into 132×324 display coordinates. */
export function mapCopPointToDisplay(
  point: CopPoint,
  side: FootSide,
  canvasWidth: number,
): CopPoint {
  const mapped = copToDisplayCoords(point.x, point.y, side, canvasWidth)
  return { ...point, x: mapped.x, y: mapped.y }
}

export function mapCopPointsToDisplay(
  copPoints: readonly CopPoint[],
  side: FootSide,
  canvasWidth: number,
): CopPoint[] {
  return copPoints.map((point) => mapCopPointToDisplay(point, side, canvasWidth))
}

/**
 * Normalize COP points into the current 132×324 display space.
 *
 * Older gait endpoints emitted the pre-y=x display coordinates as
 * `{ x: cy, y: mirroredCx }` in a 324×132 space. Those points are visually
 * horizontal on the corrected foot image, so swap them back when detected.
 */
export function normalizeCopPointsForDisplay(
  copPoints: readonly CopPoint[],
  displayWidth: number,
  displayHeight: number,
): CopPoint[] {
  let maxX = Number.NEGATIVE_INFINITY
  let maxY = Number.NEGATIVE_INFINITY
  let minX = Number.POSITIVE_INFINITY
  let minY = Number.POSITIVE_INFINITY
  let finiteCount = 0

  for (const point of copPoints) {
    if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) {
      continue
    }
    finiteCount += 1
    minX = Math.min(minX, point.x)
    minY = Math.min(minY, point.y)
    maxX = Math.max(maxX, point.x)
    maxY = Math.max(maxY, point.y)
  }

  if (finiteCount === 0) {
    return [...copPoints]
  }

  const xSpan = maxX - minX
  const ySpan = maxY - minY
  const isPortraitDisplay = displayHeight > displayWidth
  const exceedsPortraitWidth = maxX >= displayWidth && maxX <= displayHeight && maxY <= displayWidth
  const hasHorizontalMainAxis = isPortraitDisplay && xSpan > ySpan * 1.5
  const looksTransposed = exceedsPortraitWidth || hasHorizontalMainAxis
  if (!looksTransposed) {
    return [...copPoints]
  }

  return copPoints.map((point) => ({ ...point, x: point.y, y: point.x }))
}
