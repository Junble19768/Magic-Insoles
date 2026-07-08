import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { setBoundaryAssetsForTest } from '@/viz/boundary/assets'
import {
  copToDisplayCoords,
  mapCopPointToDisplay,
  normalizeCopPointsForDisplay,
} from '@/viz/boundary/transform'
import type { BoundaryAssets } from '@/viz/boundary/types'

const assetsPath = resolve(__dirname, '../../../../public/data/boundary_assets.json')
const assets = JSON.parse(readFileSync(assetsPath, 'utf-8')) as BoundaryAssets

setBoundaryAssetsForTest(assets)

describe('copToDisplayCoords', () => {
  it('keeps right foot sensor centroid coordinates', () => {
    const centroid = assets.centroids[0]
    const mapped = copToDisplayCoords(centroid.cx, centroid.cy, 'right', assets.canvas.width)
    expect(mapped.x).toBeCloseTo(centroid.cx, 5)
    expect(mapped.y).toBeCloseTo(centroid.cy, 5)
  })

  it('mirrors left foot sensor centroid on X axis', () => {
    const centroid = assets.centroids[0]
    const mapped = copToDisplayCoords(centroid.cx, centroid.cy, 'left', assets.canvas.width)
    expect(mapped.x).toBeCloseTo(assets.canvas.width - 1 - centroid.cx, 5)
    expect(mapped.y).toBeCloseTo(centroid.cy, 5)
  })
})

describe('mapCopPointToDisplay', () => {
  it('maps sensor-space COP for right foot unchanged', () => {
    const centroid = assets.centroids[0]
    const mapped = mapCopPointToDisplay(
      { x: centroid.cx, y: centroid.cy, pressure: 100 },
      'right',
      assets.canvas.width,
    )
    expect(mapped.x).toBeCloseTo(centroid.cx, 5)
    expect(mapped.y).toBeCloseTo(centroid.cy, 5)
    expect(mapped.pressure).toBe(100)
  })

  it('maps sensor-space COP for left foot with X mirror', () => {
    const centroid = assets.centroids[0]
    const mapped = mapCopPointToDisplay(
      { x: centroid.cx, y: centroid.cy, pressure: 120 },
      'left',
      assets.canvas.width,
    )
    expect(mapped.x).toBeCloseTo(assets.canvas.width - 1 - centroid.cx, 5)
    expect(mapped.y).toBeCloseTo(centroid.cy, 5)
    expect(mapped.pressure).toBe(120)
  })
})

describe('normalizeCopPointsForDisplay', () => {
  it('keeps current 132x324 display-space COP points unchanged', () => {
    const points = [
      { x: 50, y: 260, pressure: 100 },
      { x: 54, y: 180, pressure: 110 },
      { x: 58, y: 90, pressure: 120 },
    ]

    expect(normalizeCopPointsForDisplay(points, assets.canvas.width, assets.canvas.height)).toEqual(points)
  })

  it('swaps legacy 324x132 transposed COP points back to 132x324 display space', () => {
    const legacyPoints = [
      { x: 260, y: 50, pressure: 100 },
      { x: 180, y: 54, pressure: 110 },
      { x: 90, y: 58, pressure: 120 },
    ]

    expect(normalizeCopPointsForDisplay(legacyPoints, assets.canvas.width, assets.canvas.height)).toEqual([
      { x: 50, y: 260, pressure: 100 },
      { x: 54, y: 180, pressure: 110 },
      { x: 58, y: 90, pressure: 120 },
    ])
  })

  it('swaps legacy horizontal points by main-axis span even within portrait width', () => {
    const legacyPoints = [
      { x: 40, y: 50, pressure: 100 },
      { x: 80, y: 54, pressure: 110 },
      { x: 120, y: 58, pressure: 120 },
    ]

    expect(normalizeCopPointsForDisplay(legacyPoints, assets.canvas.width, assets.canvas.height)).toEqual([
      { x: 50, y: 40, pressure: 100 },
      { x: 54, y: 80, pressure: 110 },
      { x: 58, y: 120, pressure: 120 },
    ])
  })
})
