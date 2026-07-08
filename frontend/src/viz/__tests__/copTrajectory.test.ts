import { describe, expect, it } from 'vitest'
import { fitCopTrajectoryLine, fitLineSegment } from '@/viz/cop'

describe('fitCopTrajectoryLine', () => {
  it('returns ~0° for vertical trajectory', () => {
    const xs = [10, 10, 10, 10]
    const ys = [20, 40, 60, 80]
    const fit = fitCopTrajectoryLine(xs, ys)
    expect(fit).not.toBeNull()
    expect(fit?.angleDeg).toBeLessThan(5)
    expect(fit?.pointCount).toBe(4)
  })

  it('returns ~45° for diagonal trajectory', () => {
    const xs = [0, 10, 20, 30]
    const ys = [0, 10, 20, 30]
    const fit = fitCopTrajectoryLine(xs, ys)
    expect(fit).not.toBeNull()
    expect(fit?.angleDeg).toBeGreaterThan(40)
    expect(fit?.angleDeg).toBeLessThan(50)
  })

  it('returns null when fewer than min points', () => {
    expect(fitCopTrajectoryLine([1], [2])).toBeNull()
  })
})

describe('fitLineSegment', () => {
  it('spans projections of input points', () => {
    const xs = [0, 0, 0]
    const ys = [10, 50, 90]
    const fit = fitCopTrajectoryLine(xs, ys)
    expect(fit).not.toBeNull()
    if (!fit) {
      return
    }
    const [p0, p1] = fitLineSegment(fit, xs, ys)
    const extent = Math.hypot(p1.x - p0.x, p1.y - p0.y)
    expect(extent).toBeGreaterThan(70)
  })
})
