import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { setBoundaryAssetsForTest } from '@/viz/boundary/assets'
import { buildBoundaryFootHeatmap } from '@/viz/boundary/heatmap'
import type { BoundaryAssets } from '@/viz/boundary/types'

const assetsPath = resolve(__dirname, '../../../../public/data/boundary_assets.json')
const assets = JSON.parse(readFileSync(assetsPath, 'utf-8')) as BoundaryAssets

setBoundaryAssetsForTest(assets)

describe('buildBoundaryFootHeatmap', () => {
  it('places non-zero pixels only inside activated sensor regions', () => {
    const values = new Array(16).fill(0)
    values[0] = 200

    const result = buildBoundaryFootHeatmap(assets, values, 'right', 0)
    let nonZero = 0
    for (let i = 0; i < result.field.length; i += 1) {
      if (result.field[i] > 0) {
        nonZero += 1
      }
    }

    expect(result.peak).toBe(200)
    expect(nonZero).toBeGreaterThan(0)
    expect(nonZero).toBeLessThan(result.field.length)
  })

  it('mirrors left foot layout differently from right', () => {
    const values = new Array(16).fill(0)
    values[0] = 150

    const left = buildBoundaryFootHeatmap(assets, values, 'left', 0)
    const right = buildBoundaryFootHeatmap(assets, values, 'right', 0)

    let leftSum = 0
    let rightSum = 0
    for (let i = 0; i < left.field.length; i += 1) {
      leftSum += left.field[i]
      rightSum += right.field[i]
    }

    expect(leftSum).toBeCloseTo(rightSum, 5)
    expect(left.field).not.toEqual(right.field)
  })
})
