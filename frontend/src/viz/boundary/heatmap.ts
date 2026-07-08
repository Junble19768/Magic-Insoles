import { decodeRleMask, getBoundaryAssets } from '@/viz/boundary/assets'
import { gaussianBlur } from '@/viz/boundary/blur'
import { transformFieldForDisplay } from '@/viz/boundary/transform'
import type { BoundaryAssets, FootSide } from '@/viz/boundary/types'

export const BOUNDARY_BLUR_SIGMA = 3

export interface BoundaryHeatmapResult {
  field: Float32Array
  displayWidth: number
  displayHeight: number
  peak: number
}

function fillSensorField(
  assets: BoundaryAssets,
  values: readonly number[],
): Float32Array {
  const { width, height } = assets.canvas
  const field = new Float32Array(width * height)

  for (const maskMeta of assets.masks) {
    const value = values[maskMeta.fsrIndex] ?? 0
    if (!Number.isFinite(value) || value <= 0) {
      continue
    }
    const mask = decodeRleMask(maskMeta.rle, maskMeta.width, maskMeta.height, maskMeta.startsWith)
    for (let i = 0; i < mask.length; i += 1) {
      if (mask[i]) {
        field[i] = Math.max(field[i], value)
      }
    }
  }

  return field
}

export function buildBoundaryFootHeatmap(
  assets: BoundaryAssets,
  values: readonly number[],
  side: FootSide,
  blurSigma = BOUNDARY_BLUR_SIGMA,
): BoundaryHeatmapResult {
  const { width, height } = assets.canvas
  let field = fillSensorField(assets, values)
  field = gaussianBlur(field, width, height, blurSigma)

  let peak = 0
  for (let i = 0; i < field.length; i += 1) {
    if (field[i] > peak) {
      peak = field[i]
    }
  }

  const transformed = transformFieldForDisplay(field, width, height, side)
  return {
    field: transformed.field,
    displayWidth: transformed.displayWidth,
    displayHeight: transformed.displayHeight,
    peak,
  }
}

export function buildBoundaryFootHeatmapFromCache(
  values: readonly number[],
  side: FootSide,
  blurSigma = BOUNDARY_BLUR_SIGMA,
): BoundaryHeatmapResult | null {
  const assets = getBoundaryAssets()
  if (!assets) {
    return null
  }
  return buildBoundaryFootHeatmap(assets, values, side, blurSigma)
}
