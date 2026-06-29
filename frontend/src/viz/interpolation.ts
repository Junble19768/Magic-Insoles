/**
 * Map normalized pressure (0-1) to heatmap color.
 * Blue -> Green -> Yellow -> Red
 */
export function pressureToColor(pressure: number): [number, number, number] {
  const value = Math.max(0, Math.min(1, pressure))

  if (value < 0.33) {
    const t = value / 0.33
    return [0, t, 1 - t * 0.5]
  }

  if (value < 0.66) {
    const t = (value - 0.33) / 0.33
    return [t, 1, 0]
  }

  const t = (value - 0.66) / 0.34
  return [1, 1 - t, 0]
}

/**
 * Interpolate pressure at a point using inverse-distance weighting.
 */
export function interpolatePressure(
  x: number,
  y: number,
  pressures: readonly number[],
  layout: readonly { x: number; y: number }[],
): number {
  let weightedSum = 0
  let totalWeight = 0

  layout.forEach((sensor, index) => {
    const dx = x - sensor.x
    const dy = y - sensor.y
    const distance = Math.sqrt(dx * dx + dy * dy)
    const weight = 1 / Math.max(distance, 0.08) ** 2
    const pressure = pressures[index] ?? 0

    weightedSum += pressure * weight
    totalWeight += weight
  })

  if (totalWeight === 0) {
    return 0
  }

  return weightedSum / totalWeight / 255
}
