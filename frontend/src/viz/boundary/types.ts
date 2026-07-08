export interface BoundaryCentroid {
  fsrIndex: number
  cx: number
  cy: number
}

export interface BoundaryMaskRle {
  fsrIndex: number
  width: number
  height: number
  rle: readonly number[]
  startsWith: number
}

export interface BoundaryAssets {
  schema: string
  canvas: { width: number; height: number }
  centroids: readonly BoundaryCentroid[]
  masks: readonly BoundaryMaskRle[]
}

export type FootSide = 'left' | 'right'
