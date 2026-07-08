import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import {
  buildBoundaryFootHeatmap,
  composeFootHeatmapImage,
  drawTrajectoryOverlays,
  loadBoundaryAssets,
  normalizeCopPointsForDisplay,
} from '@/viz/boundary'
import {
  copPointsToPlotArrays,
  fitCopTrajectoryLine,
  fitLineSegment,
} from '@/viz/cop'
import type { CopPoint } from '@/types'

interface FootAnalysisCanvasProps {
  pressures: readonly number[]
  copPoints?: readonly CopPoint[]
  side: 'left' | 'right'
  showTrajectoryDensity?: boolean
  showTrajectoryFit?: boolean
}

const PLANE_HEIGHT = 2

function updateCameraForAspect(
  camera: THREE.OrthographicCamera,
  displayWidth: number,
  displayHeight: number,
): void {
  const aspect = displayWidth / displayHeight
  if (aspect >= 1) {
    camera.left = -PLANE_HEIGHT / 2
    camera.right = PLANE_HEIGHT / 2
    camera.top = PLANE_HEIGHT / 2 / aspect
    camera.bottom = -PLANE_HEIGHT / 2 / aspect
  } else {
    camera.left = -PLANE_HEIGHT / 2 * aspect
    camera.right = PLANE_HEIGHT / 2 * aspect
    camera.top = PLANE_HEIGHT / 2
    camera.bottom = -PLANE_HEIGHT / 2
  }
  camera.updateProjectionMatrix()
}

function updatePlaneGeometry(
  mesh: THREE.Mesh,
  displayWidth: number,
  displayHeight: number,
): void {
  const aspect = displayWidth / displayHeight
  const planeWidth = PLANE_HEIGHT * aspect
  mesh.geometry.dispose()
  mesh.geometry = new THREE.PlaneGeometry(planeWidth, PLANE_HEIGHT)
}

function imageDataToTexture(image: ImageData): THREE.DataTexture {
  const texture = new THREE.DataTexture(
    image.data,
    image.width,
    image.height,
    THREE.RGBAFormat,
  )
  texture.needsUpdate = true
  texture.flipY = true
  texture.minFilter = THREE.LinearFilter
  texture.magFilter = THREE.LinearFilter
  return texture
}

function syncRendererSize(
  renderer: THREE.WebGLRenderer,
  container: HTMLDivElement,
): void {
  renderer.setSize(container.clientWidth, container.clientHeight, false)
  renderer.domElement.style.display = 'block'
  renderer.domElement.style.width = '100%'
  renderer.domElement.style.height = '100%'
}

export function FootAnalysisCanvas({
  pressures,
  copPoints = [],
  side,
  showTrajectoryDensity = false,
  showTrajectoryFit = false,
}: FootAnalysisCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return undefined
    }

    let disposed = false

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#f4f7f5')

    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10)
    camera.position.z = 2

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    container.appendChild(renderer.domElement)

    const material = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide })
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), material)
    scene.add(mesh)

    let texture: THREE.DataTexture | null = null
    let displayWidth = 0
    let displayHeight = 0

    const renderScene = (
      image: ImageData,
      width: number,
      height: number,
      fitSegment: [{ x: number; y: number }, { x: number; y: number }] | null,
      displayCopPoints: readonly CopPoint[],
    ): void => {
      if (disposed) {
        return
      }

      displayWidth = width
      displayHeight = height
      updateCameraForAspect(camera, displayWidth, displayHeight)
      updatePlaneGeometry(mesh, displayWidth, displayHeight)

      const overlayCanvas = document.createElement('canvas')
      drawTrajectoryOverlays(
        overlayCanvas,
        image,
        displayCopPoints,
        displayWidth,
        displayHeight,
        fitSegment,
      )

      const overlayCtx = overlayCanvas.getContext('2d')
      if (!overlayCtx) {
        return
      }
      const finalImage = overlayCtx.getImageData(0, 0, displayWidth, displayHeight)

      texture?.dispose()
      texture = imageDataToTexture(finalImage)
      material.map = texture
      material.needsUpdate = true

      syncRendererSize(renderer, container)
      renderer.render(scene, camera)
    }

    const handleResize = (): void => {
      if (disposed || !texture || displayWidth === 0 || displayHeight === 0) {
        return
      }
      updateCameraForAspect(camera, displayWidth, displayHeight)
      updatePlaneGeometry(mesh, displayWidth, displayHeight)
      syncRendererSize(renderer, container)
      renderer.render(scene, camera)
    }

    window.addEventListener('resize', handleResize)

    void loadBoundaryAssets()
      .then((assets) => {
        if (disposed) {
          return
        }

        const { width, height } = assets.canvas
        container.style.aspectRatio = `${width} / ${height}`

        const heatmap = buildBoundaryFootHeatmap(assets, pressures, side)
        const displayCopPoints = normalizeCopPointsForDisplay(
          copPoints,
          heatmap.displayWidth,
          heatmap.displayHeight,
        )
        const image = composeFootHeatmapImage(heatmap, {
          showTrajectoryDensity,
          copPoints: displayCopPoints,
        })

        let fitSegment: [{ x: number; y: number }, { x: number; y: number }] | null = null
        if (showTrajectoryFit && displayCopPoints.length >= 2) {
          const { xs, ys } = copPointsToPlotArrays(displayCopPoints)
          const fit = fitCopTrajectoryLine(xs, ys)
          if (fit) {
            fitSegment = fitLineSegment(fit, xs, ys)
          }
        }

        renderScene(image, heatmap.displayWidth, heatmap.displayHeight, fitSegment, displayCopPoints)
      })
      .catch((error: unknown) => {
        console.error('FootAnalysisCanvas failed to load boundary assets', error)
      })

    return () => {
      disposed = true
      window.removeEventListener('resize', handleResize)
      texture?.dispose()
      mesh.geometry.dispose()
      renderer.dispose()
      material.dispose()
      container.innerHTML = ''
    }
  }, [pressures, copPoints, side, showTrajectoryDensity, showTrajectoryFit])

  return <div className="gait-foot__canvas" ref={containerRef} />
}
