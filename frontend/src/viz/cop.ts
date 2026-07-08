import { getBoundaryAssets } from '@/viz/boundary/assets'
import { copToDisplayCoords } from '@/viz/boundary/transform'
import type { FootSide } from '@/viz/boundary/types'
import type { BalanceGrade, BalanceResult, CopPoint, PressureFrame } from '@/types'

export const COP_TRAJECTORY_MIN_POINTS = 2

export interface CopLineFit {
  angleDeg: number
  centroid: { x: number; y: number }
  direction: { x: number; y: number }
  pointCount: number
}

/**
 * Compute center of pressure for one foot using boundary region centroids.
 * Returns plot coordinates (x: 0..canvasWidth-1, y: 0..canvasHeight-1).
 */
export function calculateCop(pressures: readonly number[], side: FootSide): CopPoint {
  const assets = getBoundaryAssets()
  if (!assets) {
    return { x: 0, y: 0, pressure: 0 }
  }

  const canvasWidth = assets.canvas.width
  let weightedX = 0
  let weightedY = 0
  let totalPressure = 0

  for (const { fsrIndex, cx, cy } of assets.centroids) {
    const pressure = pressures[fsrIndex] ?? 0
    if (!Number.isFinite(pressure) || pressure <= 0) {
      continue
    }
    const plot = copToDisplayCoords(cx, cy, side, canvasWidth)
    weightedX += plot.x * pressure
    weightedY += plot.y * pressure
    totalPressure += pressure
  }

  if (totalPressure <= 0) {
    return { x: Number.NaN, y: Number.NaN, pressure: 0 }
  }

  return {
    x: weightedX / totalPressure,
    y: weightedY / totalPressure,
    pressure: totalPressure,
  }
}

/** Fit a line to COP trajectory points via SVD; angle measured from +Y axis. */
export function fitCopTrajectoryLine(
  xs: readonly number[],
  ys: readonly number[],
  minPoints = COP_TRAJECTORY_MIN_POINTS,
): CopLineFit | null {
  const points: { x: number; y: number }[] = []
  for (let i = 0; i < xs.length; i += 1) {
    const x = xs[i]
    const y = ys[i]
    if (Number.isFinite(x) && Number.isFinite(y)) {
      points.push({ x, y })
    }
  }
  if (points.length < minPoints) {
    return null
  }

  let meanX = 0
  let meanY = 0
  for (const p of points) {
    meanX += p.x
    meanY += p.y
  }
  meanX /= points.length
  meanY /= points.length

  let sxx = 0
  let sxy = 0
  let syy = 0
  for (const p of points) {
    const dx = p.x - meanX
    const dy = p.y - meanY
    sxx += dx * dx
    sxy += dx * dy
    syy += dy * dy
  }

  const trace = sxx + syy
  const det = sxx * syy - sxy * sxy
  const gap = Math.sqrt(Math.max(0, trace * trace / 4 - det))
  const lambda1 = trace / 2 + gap

  let dx = sxy
  let dy = lambda1 - sxx
  if (Math.abs(dx) < 1e-12 && Math.abs(dy) < 1e-12) {
    dx = lambda1 - syy
    dy = sxy
  }
  if (dy < 0) {
    dx = -dx
    dy = -dy
  }

  const norm = Math.hypot(dx, dy)
  if (norm <= 0) {
    return null
  }
  dx /= norm
  dy /= norm

  const angleDeg = (Math.atan2(Math.abs(dx), Math.abs(dy)) * 180) / Math.PI

  return {
    angleDeg,
    centroid: { x: meanX, y: meanY },
    direction: { x: dx, y: dy },
    pointCount: points.length,
  }
}

export function fitLineSegment(
  fit: CopLineFit,
  xs: readonly number[],
  ys: readonly number[],
): [{ x: number; y: number }, { x: number; y: number }] {
  const { x: cx, y: cy } = fit.centroid
  const { x: dx, y: dy } = fit.direction

  let tMin = 0
  let tMax = 0
  let hasProjection = false

  for (let i = 0; i < xs.length; i += 1) {
    const x = xs[i]
    const y = ys[i]
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      continue
    }
    const t = (x - cx) * dx + (y - cy) * dy
    if (!hasProjection) {
      tMin = t
      tMax = t
      hasProjection = true
    } else {
      tMin = Math.min(tMin, t)
      tMax = Math.max(tMax, t)
    }
  }

  if (!hasProjection) {
    return [
      { x: cx - dx, y: cy - dy },
      { x: cx + dx, y: cy + dy },
    ]
  }

  return [
    { x: cx + dx * tMin, y: cy + dy * tMin },
    { x: cx + dx * tMax, y: cy + dy * tMax },
  ]
}

export function copPointsToPlotArrays(copPoints: readonly CopPoint[]): {
  xs: number[]
  ys: number[]
} {
  const xs: number[] = []
  const ys: number[] = []
  for (const point of copPoints) {
    if (Number.isFinite(point.x) && Number.isFinite(point.y)) {
      xs.push(point.x)
      ys.push(point.y)
    }
  }
  return { xs, ys }
}

/**
 * Evaluate balance based on COP trajectory stability over sampled frames.
 */
export function calculateBalanceScore(frames: readonly PressureFrame[]): BalanceResult {
  if (frames.length === 0) {
    return {
      score: 0,
      grade: 'needs_improvement',
      leftCopTrajectory: [],
      rightCopTrajectory: [],
      leftAvgPressures: Array.from({ length: 16 }, () => 0),
      rightAvgPressures: Array.from({ length: 16 }, () => 0),
      swayArea: 0,
      copStdDev: 0,
      timestamp: Date.now(),
    }
  }

  const leftCops: CopPoint[] = []
  const rightCops: CopPoint[] = []
  const leftPressureSums = new Array(16).fill(0)
  const rightPressureSums = new Array(16).fill(0)

  frames.forEach((frame) => {
    const l = calculateCop(frame.leftFoot, 'left')
    const r = calculateCop(frame.rightFoot, 'right')
    leftCops.push(l)
    rightCops.push(r)

    frame.leftFoot.forEach((v, i) => { leftPressureSums[i] += v })
    frame.rightFoot.forEach((v, i) => { rightPressureSums[i] += v })
  })

  const len = frames.length
  const leftAvgPressures = leftPressureSums.map((v: number) => Math.round(v / len))
  const rightAvgPressures = rightPressureSums.map((v: number) => Math.round(v / len))

  const allCops = [...leftCops, ...rightCops].filter(
    (c) => Number.isFinite(c.x) && Number.isFinite(c.y),
  )

  if (allCops.length === 0) {
    return {
      score: 0,
      grade: 'needs_improvement',
      leftCopTrajectory: leftCops,
      rightCopTrajectory: rightCops,
      leftAvgPressures,
      rightAvgPressures,
      swayArea: 0,
      copStdDev: 0,
      timestamp: Date.now(),
    }
  }

  let meanX = 0
  let meanY = 0
  allCops.forEach((c) => { meanX += c.x; meanY += c.y })
  meanX /= allCops.length
  meanY /= allCops.length

  let sumSqX = 0
  let sumSqY = 0
  allCops.forEach((c) => {
    sumSqX += (c.x - meanX) ** 2
    sumSqY += (c.y - meanY) ** 2
  })
  const stdDevX = Math.sqrt(sumSqX / allCops.length)
  const stdDevY = Math.sqrt(sumSqY / allCops.length)
  const copStdDev = Math.sqrt(stdDevX ** 2 + stdDevY ** 2)

  const swayArea = Math.PI * stdDevX * 2 * stdDevY * 2
  const rawScore = 100 - (swayArea * 0.05 + copStdDev * 0.2)
  const score = Math.max(0, Math.min(100, Math.round(rawScore)))

  let grade: BalanceGrade = 'good'
  if (score >= 85) grade = 'excellent'
  else if (score >= 70) grade = 'good'
  else if (score >= 55) grade = 'fair'
  else grade = 'needs_improvement'

  return {
    score,
    grade,
    leftCopTrajectory: leftCops,
    rightCopTrajectory: rightCops,
    leftAvgPressures,
    rightAvgPressures,
    swayArea,
    copStdDev,
    timestamp: Date.now(),
  }
}
