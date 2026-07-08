import { pressureToColor } from '@/viz/interpolation'
import type { CopPoint } from '@/types'
import { buildCopDensityField } from '@/viz/boundary/trajectoryHeatmap'
import type { BoundaryHeatmapResult } from '@/viz/boundary/heatmap'

export interface CompositeLayers {
  showTrajectoryDensity?: boolean
  trajectoryAlpha?: number
  copPoints?: readonly CopPoint[]
}

const TRAJECTORY_COLOR: [number, number, number] = [80 / 255, 220 / 255, 220 / 255]
const FIT_LINE_COLOR: [number, number, number] = [255 / 255, 220 / 255, 80 / 255]

export function fieldToImageData(
  field: Float32Array,
  width: number,
  height: number,
  peak: number,
  pressureMode = false,
): ImageData {
  const denom = pressureMode ? Math.max(peak, 100) : Math.max(peak, 0.01)
  const pixels = new Uint8ClampedArray(width * height * 4)

  for (let plotY = 0; plotY < height; plotY += 1) {
    for (let plotX = 0; plotX < width; plotX += 1) {
      const value = field[plotY * width + plotX] / denom
      const [r, g, b] = pressureToColor(value)
      const offset = (plotY * width + plotX) * 4
      pixels[offset] = Math.round(r * 255)
      pixels[offset + 1] = Math.round(g * 255)
      pixels[offset + 2] = Math.round(b * 255)
      pixels[offset + 3] = 255
    }
  }

  return new ImageData(pixels, width, height)
}

export function overlayDensityHeatmap(
  base: ImageData,
  densityField: Float32Array,
  alpha = 0.55,
): void {
  let peak = 0
  for (let i = 0; i < densityField.length; i += 1) {
    if (densityField[i] > peak) {
      peak = densityField[i]
    }
  }
  if (peak <= 0) {
    return
  }

  const { width, height } = base
  const [tr, tg, tb] = TRAJECTORY_COLOR

  for (let plotY = 0; plotY < height; plotY += 1) {
    for (let plotX = 0; plotX < width; plotX += 1) {
      const normalized = densityField[plotY * width + plotX] / peak
      if (normalized <= 0.01) {
        continue
      }
      const offset = (plotY * width + plotX) * 4
      const blend = Math.min(1, normalized * alpha)
      base.data[offset] = Math.round(base.data[offset] * (1 - blend) + tr * 255 * blend)
      base.data[offset + 1] = Math.round(base.data[offset + 1] * (1 - blend) + tg * 255 * blend)
      base.data[offset + 2] = Math.round(base.data[offset + 2] * (1 - blend) + tb * 255 * blend)
    }
  }
}

export function drawCopTrajectory(
  ctx: CanvasRenderingContext2D,
  copPoints: readonly CopPoint[],
  displayWidth: number,
  displayHeight: number,
): void {
  if (copPoints.length < 2) {
    return
  }

  const [r, g, b] = TRAJECTORY_COLOR
  ctx.strokeStyle = `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, 0.85)`
  ctx.lineWidth = 2
  ctx.beginPath()

  let started = false
  for (const point of copPoints) {
    if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) {
      started = false
      continue
    }
    const px = point.x
    const py = point.y
    if (px < 0 || px >= displayWidth || py < 0 || py >= displayHeight) {
      started = false
      continue
    }
    if (!started) {
      ctx.moveTo(px, py)
      started = true
    } else {
      ctx.lineTo(px, py)
    }
  }
  ctx.stroke()
}

export function drawFitLine(
  ctx: CanvasRenderingContext2D,
  p0: { x: number; y: number },
  p1: { x: number; y: number },
): void {
  const [r, g, b] = FIT_LINE_COLOR
  ctx.strokeStyle = `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, 0.86)`
  ctx.lineWidth = 2
  ctx.setLineDash([6, 4])
  ctx.beginPath()
  ctx.moveTo(p0.x, p0.y)
  ctx.lineTo(p1.x, p1.y)
  ctx.stroke()
  ctx.setLineDash([])
}

export function composeFootHeatmapImage(
  heatmap: BoundaryHeatmapResult,
  layers: CompositeLayers = {},
): ImageData {
  const image = fieldToImageData(
    heatmap.field,
    heatmap.displayWidth,
    heatmap.displayHeight,
    heatmap.peak,
    false,
  )

  if (layers.showTrajectoryDensity && layers.copPoints && layers.copPoints.length > 0) {
    const density = buildCopDensityField(layers.copPoints, {
      displayWidth: heatmap.displayWidth,
      displayHeight: heatmap.displayHeight,
    })
    overlayDensityHeatmap(image, density, layers.trajectoryAlpha ?? 0.55)
  }

  return image
}

export function drawTrajectoryOverlays(
  canvas: HTMLCanvasElement,
  image: ImageData,
  copPoints: readonly CopPoint[],
  displayWidth: number,
  displayHeight: number,
  fitSegment: [{ x: number; y: number }, { x: number; y: number }] | null,
): void {
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return
  }
  canvas.width = displayWidth
  canvas.height = displayHeight
  ctx.putImageData(image, 0, 0)
  drawCopTrajectory(ctx, copPoints, displayWidth, displayHeight)
  if (fitSegment) {
    drawFitLine(ctx, fitSegment[0], fitSegment[1])
  }
}
