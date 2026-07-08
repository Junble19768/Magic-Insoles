import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { setBoundaryAssetsForTest } from '@/viz/boundary/assets'
import type { BoundaryAssets } from '@/viz/boundary/types'
import { calculateBalanceScore, calculateCop } from '@/viz/cop'
import { createMockFrame } from '@/ble/mockData'
import type { PressureFrame } from '@/types'

const assetsPath = resolve(__dirname, '../../../public/data/boundary_assets.json')
const assets = JSON.parse(readFileSync(assetsPath, 'utf-8')) as BoundaryAssets
setBoundaryAssetsForTest(assets)

function zeroFoot(): readonly number[] {
  return new Array(16).fill(0)
}

function buildSingleSensorFoot(fsrIndex: number, value: number): number[] {
  const foot = new Array(16).fill(0)
  foot[fsrIndex] = value
  return foot
}

function makeFrame(leftFoot: readonly number[], rightFoot: readonly number[]): PressureFrame {
  return {
    frameType: 1,
    seq: 0,
    pressures: [...leftFoot, ...rightFoot],
    leftFoot,
    rightFoot,
    gaitState: 'standing',
    mlClass: 'normal',
    mlConf: 1,
    stepCount: 0,
    battery: 80,
  }
}

describe('calculateCop', () => {
  it('returns NaN COP for zero pressures', () => {
    const result = calculateCop(zeroFoot(), 'left')
    expect(result.pressure).toBe(0)
    expect(Number.isNaN(result.x)).toBe(true)
    expect(Number.isNaN(result.y)).toBe(true)
  })

  it('returns centroid of active sensor region', () => {
    const centroid = assets.centroids[0]
    const result = calculateCop(buildSingleSensorFoot(0, 100), 'right')
    expect(result.x).toBeCloseTo(centroid.cx, 1)
    expect(result.y).toBeCloseTo(centroid.cy, 1)
    expect(result.pressure).toBe(100)
  })

  it('mirrors left foot COP on X axis', () => {
    const centroid = assets.centroids[0]
    const result = calculateCop(buildSingleSensorFoot(0, 100), 'left')
    expect(result.x).toBeCloseTo(assets.canvas.width - 1 - centroid.cx, 1)
    expect(result.y).toBeCloseTo(centroid.cy, 1)
  })
})

describe('calculateBalanceScore', () => {
  it('perfect still standing gets high score', () => {
    const foot = buildSingleSensorFoot(0, 100)
    const frames: PressureFrame[] = Array.from({ length: 300 }, () => makeFrame(foot, foot))
    const result = calculateBalanceScore(frames)
    expect(result.score).toBeGreaterThanOrEqual(85)
    expect(result.grade).toBe('excellent')
  })

  it('extreme sway gets low score', () => {
    const frames: PressureFrame[] = Array.from({ length: 300 }, (_, i) => {
      const sensor = i % 16
      return makeFrame(
        buildSingleSensorFoot(sensor, 200),
        buildSingleSensorFoot((sensor + 1) % 16, 200),
      )
    })
    const result = calculateBalanceScore(frames)
    expect(result.score).toBeLessThan(85)
  })

  it('only left foot has pressure', () => {
    const foot = buildSingleSensorFoot(0, 120)
    const frames: PressureFrame[] = Array.from({ length: 300 }, () => ({
      ...makeFrame(foot, zeroFoot()),
      pressures: [...foot, ...zeroFoot()],
    }))
    const result = calculateBalanceScore(frames)
    expect(result.leftAvgPressures.some((v) => v > 0)).toBe(true)
  })

  it('only right foot has pressure', () => {
    const foot = buildSingleSensorFoot(0, 120)
    const frames: PressureFrame[] = Array.from({ length: 300 }, () => ({
      ...makeFrame(zeroFoot(), foot),
      pressures: [...zeroFoot(), ...foot],
    }))
    const result = calculateBalanceScore(frames)
    expect(result.rightAvgPressures.some((v) => v > 0)).toBe(true)
  })

  it('all-zero frames returns 0 score', () => {
    const empty: PressureFrame[] = []
    const result = calculateBalanceScore(empty)
    expect(result.score).toBe(0)
    expect(result.grade).toBe('needs_improvement')
  })

  it('fewer frames produce valid result', () => {
    const frames = Array.from({ length: 100 }, () => createMockFrame())
    const result = calculateBalanceScore(frames)
    expect(result.score).toBeGreaterThanOrEqual(0)
    expect(result.score).toBeLessThanOrEqual(100)
    expect(['excellent', 'good', 'fair', 'needs_improvement']).toContain(result.grade)
  })

  it('alternating sensors produce measurable stdDev', () => {
    const frames: PressureFrame[] = []
    for (let i = 0; i < 200; i += 1) {
      const sensor = i % 2 === 0 ? 0 : 15
      frames.push(makeFrame(buildSingleSensorFoot(sensor, 200), buildSingleSensorFoot(sensor, 200)))
    }
    const result = calculateBalanceScore(frames)
    expect(result.copStdDev).toBeGreaterThan(1)
  })
})
