import { gaussianBlur } from '@/viz/boundary/blur'
import type { CopPoint } from '@/types'

export interface CopDensityOptions {
  displayWidth: number
  displayHeight: number
  kernelSigma?: number
  blurSigma?: number
}

const DEFAULT_KERNEL_SIGMA = 4
const DEFAULT_BLUR_SIGMA = 2

export function buildCopDensityField(
  copPoints: readonly CopPoint[],
  options: CopDensityOptions,
): Float32Array {
  const {
    displayWidth,
    displayHeight,
    kernelSigma = DEFAULT_KERNEL_SIGMA,
    blurSigma = DEFAULT_BLUR_SIGMA,
  } = options

  const field = new Float32Array(displayWidth * displayHeight)
  if (copPoints.length === 0) {
    return field
  }

  const radius = Math.ceil(kernelSigma * 3)
  const kernel = buildKernel(kernelSigma, radius)

  for (const point of copPoints) {
    if (!Number.isFinite(point.x) || !Number.isFinite(point.y) || point.pressure <= 0) {
      continue
    }
    splatPoint(field, displayWidth, displayHeight, point.x, point.y, point.pressure, kernel, radius)
  }

  return gaussianBlur(field, displayWidth, displayHeight, blurSigma)
}

function buildKernel(sigma: number, radius: number): Float32Array {
  const size = radius * 2 + 1
  const kernel = new Float32Array(size * size)
  let sum = 0
  for (let dy = -radius; dy <= radius; dy += 1) {
    for (let dx = -radius; dx <= radius; dx += 1) {
      const value = Math.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma))
      kernel[(dy + radius) * size + (dx + radius)] = value
      sum += value
    }
  }
  for (let i = 0; i < kernel.length; i += 1) {
    kernel[i] /= sum
  }
  return kernel
}

function splatPoint(
  field: Float32Array,
  width: number,
  height: number,
  centerX: number,
  centerY: number,
  weight: number,
  kernel: Float32Array,
  radius: number,
): void {
  const size = radius * 2 + 1
  const ix = Math.round(centerX)
  const iy = Math.round(centerY)

  for (let dy = -radius; dy <= radius; dy += 1) {
    const y = iy + dy
    if (y < 0 || y >= height) {
      continue
    }
    for (let dx = -radius; dx <= radius; dx += 1) {
      const x = ix + dx
      if (x < 0 || x >= width) {
        continue
      }
      const k = kernel[(dy + radius) * size + (dx + radius)]
      field[y * width + x] += weight * k
    }
  }}
