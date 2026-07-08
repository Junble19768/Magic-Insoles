import type { FootSide } from '@/viz/boundary/types'

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
  const displayWidth = canvasHeight
  const displayHeight = canvasWidth
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
