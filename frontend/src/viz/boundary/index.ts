export {
  decodeRleMask,
  getBoundaryAssets,
  loadBoundaryAssets,
  preloadBoundaryAssets,
} from '@/viz/boundary/assets'
export { BOUNDARY_BLUR_SIGMA, buildBoundaryFootHeatmap, buildBoundaryFootHeatmapFromCache } from '@/viz/boundary/heatmap'
export {
  composeFootHeatmapImage,
  drawTrajectoryOverlays,
  fieldToImageData,
  overlayDensityHeatmap,
} from '@/viz/boundary/render'
export { buildCopDensityField } from '@/viz/boundary/trajectoryHeatmap'
export { copToDisplayCoords, leftFootMirrorX, transformFieldForDisplay } from '@/viz/boundary/transform'
export type { BoundaryAssets, BoundaryCentroid, FootSide } from '@/viz/boundary/types'
