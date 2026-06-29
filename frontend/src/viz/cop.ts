import { getSensorLayout } from '@/viz/sensorLayout'
import type { CopPoint } from '@/types'

/**
 * Compute center of pressure for one foot (TBD-2 placeholder axes).
 */
export function calculateCop(pressures: readonly number[], side: 'left' | 'right'): CopPoint {
  const layout = getSensorLayout(side)
  let weightedX = 0
  let weightedY = 0
  let totalPressure = 0

  layout.forEach((sensor, index) => {
    const pressure = pressures[index] ?? 0
    if (pressure <= 0) {
      return
    }

    weightedX += sensor.x * pressure
    weightedY += sensor.y * pressure
    totalPressure += pressure
  })

  if (totalPressure === 0) {
    return { x: 0, y: 0, pressure: 0 }
  }

  return {
    x: weightedX / totalPressure,
    y: weightedY / totalPressure,
    pressure: totalPressure,
  }
}
