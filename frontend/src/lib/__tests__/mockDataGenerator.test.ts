import { describe, expect, it } from 'vitest'
import { generateActivityHistory, generateBalanceMockFrames, generateGaitSummary, generateGpsRoute } from '@/lib/mockDataGenerator'

describe('generateActivityHistory', () => {
  it('returns exactly 7 days', () => {
    const result = generateActivityHistory(7)
    expect(result.days).toHaveLength(7)
  })

  it('returns dates in ascending order', () => {
    const result = generateActivityHistory(7)
    for (let i = 1; i < result.days.length; i += 1) {
      expect(result.days[i].date > result.days[i - 1].date).toBe(true)
    }
  })

  it('returns 30 days when requested', () => {
    const result = generateActivityHistory(30)
    expect(result.days).toHaveLength(30)
  })
})

describe('generateGpsRoute', () => {
  it('returns points forming a near-closed loop', () => {
    const route = generateGpsRoute()
    expect(route.points.length).toBeGreaterThan(40)

    const first = route.points[0]
    const last = route.points[route.points.length - 1]

    const latDiff = Math.abs(first.lat - last.lat)
    const lngDiff = Math.abs(first.lng - last.lng)
    expect(latDiff).toBeLessThan(0.01)
    expect(lngDiff).toBeLessThan(0.01)
  })

  it('has positive distance and duration', () => {
    const route = generateGpsRoute()
    expect(route.totalDistanceKm).toBeGreaterThan(0)
    expect(route.durationMinutes).toBeGreaterThan(0)
  })
})

describe('generateGaitSummary', () => {
  it('contains COP points for both feet', () => {
    const summary = generateGaitSummary()
    expect(summary.leftFoot.copPoints.length).toBeGreaterThan(50)
    expect(summary.rightFoot.copPoints.length).toBeGreaterThan(50)
  })

  it('classifies one foot as in_toe and one as normal', () => {
    const summary = generateGaitSummary()
    const classes = [summary.leftFoot.classification, summary.rightFoot.classification]
    expect(classes).toContain('normal')
    expect(classes).toContain('in_toe')
  })
})

describe('generateBalanceMockFrames', () => {
  it('returns ~1500 frames (30s @ 50Hz)', () => {
    const frames = generateBalanceMockFrames()
    expect(frames.length).toBe(1500)
  })

  it('all frames have standing gait state', () => {
    const frames = generateBalanceMockFrames()
    expect(frames.every((f) => f.gaitState === 'standing')).toBe(true)
  })

  it('all frames have 32 pressure values', () => {
    const frames = generateBalanceMockFrames()
    expect(frames.every((f) => f.pressures.length === 32)).toBe(true)
  })
})
