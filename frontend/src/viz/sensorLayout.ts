/**
 * Placeholder sensor layout (TBD-1):
 * 4x4 grid per foot, index 0 = forefoot lateral, index 15 = heel medial.
 */
export interface SensorPosition {
  index: number
  x: number
  y: number
}

const GRID_SIZE = 4

function buildFootLayout(mirrorX: boolean): SensorPosition[] {
  const positions: SensorPosition[] = []

  for (let index = 0; index < 16; index += 1) {
    const row = Math.floor(index / GRID_SIZE)
    const col = index % GRID_SIZE
    const normalizedCol = mirrorX ? GRID_SIZE - 1 - col : col

    positions.push({
      index,
      x: (normalizedCol / (GRID_SIZE - 1)) * 2 - 1,
      y: (row / (GRID_SIZE - 1)) * 2 - 1,
    })
  }

  return positions
}

export const LEFT_FOOT_LAYOUT = buildFootLayout(false)
export const RIGHT_FOOT_LAYOUT = buildFootLayout(true)

export function getSensorLayout(side: 'left' | 'right'): readonly SensorPosition[] {
  return side === 'left' ? LEFT_FOOT_LAYOUT : RIGHT_FOOT_LAYOUT
}
