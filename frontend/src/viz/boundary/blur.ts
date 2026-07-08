/** Separable Gaussian blur (BORDER_REPLICATE approximation). */
export function gaussianBlur(
  field: Float32Array,
  width: number,
  height: number,
  sigma: number,
): Float32Array {
  if (sigma <= 0) {
    return field
  }

  const kernelRadius = Math.ceil(sigma * 3)
  const kernel = buildGaussianKernel(sigma, kernelRadius)
  const temp = new Float32Array(field.length)
  const out = new Float32Array(field.length)

  blurHorizontal(field, temp, width, height, kernel, kernelRadius)
  blurVertical(temp, out, width, height, kernel, kernelRadius)
  return out
}

function buildGaussianKernel(sigma: number, radius: number): Float32Array {
  const kernel = new Float32Array(radius * 2 + 1)
  let sum = 0
  for (let i = -radius; i <= radius; i += 1) {
    const value = Math.exp(-(i * i) / (2 * sigma * sigma))
    kernel[i + radius] = value
    sum += value
  }
  for (let i = 0; i < kernel.length; i += 1) {
    kernel[i] /= sum
  }
  return kernel
}

function sampleReplicate(
  field: Float32Array,
  width: number,
  height: number,
  x: number,
  y: number,
): number {
  const clampedX = Math.max(0, Math.min(width - 1, x))
  const clampedY = Math.max(0, Math.min(height - 1, y))
  return field[clampedY * width + clampedX]
}

function blurHorizontal(
  src: Float32Array,
  dst: Float32Array,
  width: number,
  height: number,
  kernel: Float32Array,
  radius: number,
): void {
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      let sum = 0
      for (let k = -radius; k <= radius; k += 1) {
        sum += sampleReplicate(src, width, height, x + k, y) * kernel[k + radius]
      }
      dst[y * width + x] = sum
    }
  }
}

function blurVertical(
  src: Float32Array,
  dst: Float32Array,
  width: number,
  height: number,
  kernel: Float32Array,
  radius: number,
): void {
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      let sum = 0
      for (let k = -radius; k <= radius; k += 1) {
        sum += sampleReplicate(src, width, height, x, y + k) * kernel[k + radius]
      }
      dst[y * width + x] = sum
    }
  }
}
