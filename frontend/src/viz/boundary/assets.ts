import type { BoundaryAssets } from '@/viz/boundary/types'

const ASSETS_URL = `${import.meta.env.BASE_URL}data/boundary_assets.json`

let cachedAssets: BoundaryAssets | null = null
let loadPromise: Promise<BoundaryAssets> | null = null

/** Test helper: inject preloaded assets without fetch. */
export function setBoundaryAssetsForTest(assets: BoundaryAssets | null): void {
  cachedAssets = assets
  loadPromise = assets ? Promise.resolve(assets) : null
}

export function decodeRleMask(
  rle: readonly number[],
  width: number,
  height: number,
  startsWith = 0,
): Uint8Array {
  const total = width * height
  const mask = new Uint8Array(total)
  let value = startsWith
  let index = 0
  for (const run of rle) {
    for (let i = 0; i < run && index < total; i += 1) {
      mask[index] = value
      index += 1
    }
    value = 1 - value
  }
  return mask
}

export async function loadBoundaryAssets(): Promise<BoundaryAssets> {
  if (cachedAssets) {
    return cachedAssets
  }
  if (!loadPromise) {
    loadPromise = fetch(ASSETS_URL)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load boundary assets: ${response.status}`)
        }
        return response.json() as Promise<BoundaryAssets>
      })
      .then((assets) => {
        cachedAssets = assets
        return assets
      })
  }
  return loadPromise
}

/** Synchronous access after assets have been loaded. */
export function getBoundaryAssets(): BoundaryAssets | null {
  return cachedAssets
}

/** Preload boundary assets (call from app init or canvas mount). */
export function preloadBoundaryAssets(): Promise<BoundaryAssets> {
  return loadBoundaryAssets()
}

export function getBoundaryAspectRatio(assets: BoundaryAssets): number {
  return assets.canvas.width / assets.canvas.height
}
