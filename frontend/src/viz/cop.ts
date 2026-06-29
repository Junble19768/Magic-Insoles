import { getSensorLayout } from '@/viz/sensorLayout'
import type { BalanceGrade, BalanceResult, CopPoint, PressureFrame } from '@/types'

/**
 * Compute center of pressure for one foot (TBD-2 placeholder axes).
 */
export function calculateCop(pressures: readonly number[], side: 'left' | 'right'): CopPoint {
  const layout = getSensorLayout(side)
  let weightedX = 0
  let weightedY = 0
  let totalPressure = 0

  layout.forEach((sensor, index) => {
    const pressure = pressures[index] ?? 0
    if (pressure <= 0) {
      return
    }

    weightedX += sensor.x * pressure
    weightedY += sensor.y * pressure
    totalPressure += pressure
  })

  if (totalPressure === 0) {
    return { x: 0, y: 0, pressure: 0 }
  }

  return {
    x: weightedX / totalPressure,
    y: weightedY / totalPressure,
    pressure: totalPressure,
  }
}

/**
 * Evaluate balance based on COP trajectory stability over 30 seconds.
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

  // Average pressures
  const len = frames.length
  const leftAvgPressures = leftPressureSums.map((v: number) => Math.round(v / len))
  const rightAvgPressures = rightPressureSums.map((v: number) => Math.round(v / len))

  // Combine left + right COP for overall sway
  const allCops = [...leftCops, ...rightCops]

  // Mean
  let meanX = 0
  let meanY = 0
  allCops.forEach((c) => { meanX += c.x; meanY += c.y })
  meanX /= allCops.length
  meanY /= allCops.length

  // Standard deviation
  let sumSqX = 0
  let sumSqY = 0
  allCops.forEach((c) => {
    sumSqX += (c.x - meanX) ** 2
    sumSqY += (c.y - meanY) ** 2
  })
  const stdDevX = Math.sqrt(sumSqX / allCops.length)
  const stdDevY = Math.sqrt(sumSqY / allCops.length)
  const copStdDev = Math.sqrt(stdDevX ** 2 + stdDevY ** 2)

  // Sway area (95% confidence ellipse approximate area)
  const swayArea = Math.PI * stdDevX * 2 * stdDevY * 2

  // Score mapping
  const rawScore = 100 - (swayArea * 500 + copStdDev * 20)
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
