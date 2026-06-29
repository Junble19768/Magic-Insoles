import { describe, expect, it } from 'vitest'
import { calculateBalanceScore, calculateCop } from '@/viz/cop'
import { createMockFrame } from '@/ble/mockData'
import type { PressureFrame } from '@/types'

function zeroFoot(): readonly number[] {
  return new Array(16).fill(0)
}

function buildFixedFoot(cx: number, cy: number): number[] {
  return Array.from({ length: 16 }, (_, i) => {
    const row = Math.floor(i / 4)
    const col = i % 4
    const sx = col / 3
    const sy = row / 3
    const dist = Math.sqrt((sx - (cx + 1) / 2) ** 2 + (sy - (cy + 1) / 2) ** 2)
    return Math.max(0, Math.min(255, Math.round((1 / Math.max(dist, 0.05)) * 40)))
  })
}

function makeFrame(lx: number, ly: number, rx: number, ry: number): PressureFrame {
  return {
    frameType: 1,
    seq: 0,
    pressures: [...buildFixedFoot(lx, ly), ...buildFixedFoot(rx, ry)],
    leftFoot: buildFixedFoot(lx, ly),
    rightFoot: buildFixedFoot(rx, ry),
    gaitState: 'standing',
    mlClass: 'normal',
    mlConf: 1,
    stepCount: 0,
    battery: 80,
  }
}

describe('calculateCop', () => {
  it('returns zero COP for zero pressures', () => {
    const result = calculateCop(zeroFoot(), 'left')
    expect(result.x).toBe(0)
    expect(result.y).toBe(0)
    expect(result.pressure).toBe(0)
  })

  it('returns center when pressure is symmetric', () => {
    const even = new Array(16).fill(100)
    const result = calculateCop(even, 'left')
    expect(Math.abs(result.x)).toBeLessThan(0.3)
    expect(Math.abs(result.y)).toBeLessThan(0.3)
  })
})

describe('calculateBalanceScore', () => {
  it('perfect still standing gets high score', () => {
    const frames: PressureFrame[] = Array.from({ length: 300 }, () => makeFrame(0, 0, 0, 0))
    const result = calculateBalanceScore(frames)
    expect(result.score).toBeGreaterThanOrEqual(85)
    expect(result.grade).toBe('excellent')
  })

  it('extreme sway gets low score', () => {
    const frames: PressureFrame[] = Array.from({ length: 300 }, () => makeFrame(
      (Math.random() - 0.5) * 1.5,
      (Math.random() - 0.5) * 1.5,
      (Math.random() - 0.5) * 1.5,
      (Math.random() - 0.5) * 1.5,
    ))
    const result = calculateBalanceScore(frames)
    expect(result.score).toBeLessThan(50)
  })

  it('only left foot has pressure', () => {
    const frames: PressureFrame[] = Array.from({ length: 300 }, () => ({
      ...makeFrame(0, 0, 0, 0),
      rightFoot: zeroFoot(),
      pressures: [...buildFixedFoot(0, 0), ...zeroFoot()],
    }))
    const result = calculateBalanceScore(frames)
    expect(result.leftAvgPressures.some((v) => v > 0)).toBe(true)
  })

  it('only right foot has pressure', () => {
    const frames: PressureFrame[] = Array.from({ length: 300 }, () => ({
      ...makeFrame(0, 0, 0, 0),
      leftFoot: zeroFoot(),
      pressures: [...zeroFoot(), ...buildFixedFoot(0, 0)],
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

  it('known COP points produce correct stdDev', () => {
    // Generate frames with alternating extreme COPs
    const frames: PressureFrame[] = []
    for (let i = 0; i < 200; i += 1) {
      const flip = i % 2 === 0 ? 1 : -1
      frames.push(makeFrame(0.8 * flip, 0, 0.8 * flip, 0))
    }
    const result = calculateBalanceScore(frames)
    // With extreme alternating COP the sway should be significant
    expect(result.copStdDev).toBeGreaterThan(0.2)
    expect(result.copStdDev).toBeLessThan(1.2)
  })
})
