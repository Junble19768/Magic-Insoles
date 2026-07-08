import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import {
  buildBoundaryFootHeatmap,
  composeFootHeatmapImage,
  drawTrajectoryOverlays,
  loadBoundaryAssets,
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

    const geometry = new THREE.PlaneGeometry(1, 1)
    const material = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide })
    const mesh = new THREE.Mesh(geometry, material)
    scene.add(mesh)

    let texture: THREE.DataTexture | null = null

    const renderScene = (
      image: ImageData,
      displayWidth: number,
      displayHeight: number,
      fitSegment: [{ x: number; y: number }, { x: number; y: number }] | null,
    ): void => {
      if (disposed) {
        return
      }

      const aspect = displayWidth / displayHeight
      const maxSpan = 2
      if (aspect >= 1) {
        camera.left = -maxSpan / 2
        camera.right = maxSpan / 2
        camera.top = maxSpan / 2 / aspect
        camera.bottom = -maxSpan / 2 / aspect
      } else {
        camera.left = -maxSpan / 2 * aspect
        camera.right = maxSpan / 2 * aspect
        camera.top = maxSpan / 2
        camera.bottom = -maxSpan / 2
      }
      camera.updateProjectionMatrix()

      const overlayCanvas = document.createElement('canvas')
      drawTrajectoryOverlays(
        overlayCanvas,
        image,
        copPoints,
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

      renderer.setSize(container.clientWidth, container.clientHeight)
      renderer.render(scene, camera)
    }

    const handleResize = (): void => {
      if (disposed || !texture) {
        return
      }
      renderer.setSize(container.clientWidth, container.clientHeight)
      renderer.render(scene, camera)
    }

    window.addEventListener('resize', handleResize)

    void loadBoundaryAssets()
      .then((assets) => {
        if (disposed) {
          return
        }

        const heatmap = buildBoundaryFootHeatmap(assets, pressures, side)
        const image = composeFootHeatmapImage(heatmap, {
          showTrajectoryDensity,
          copPoints,
        })

        let fitSegment: [{ x: number; y: number }, { x: number; y: number }] | null = null
        if (showTrajectoryFit && copPoints.length >= 2) {
          const { xs, ys } = copPointsToPlotArrays(copPoints)
          const fit = fitCopTrajectoryLine(xs, ys)
          if (fit) {
            fitSegment = fitLineSegment(fit, xs, ys)
          }
        }

        renderScene(image, heatmap.displayWidth, heatmap.displayHeight, fitSegment)
      })
      .catch((error: unknown) => {
        console.error('FootAnalysisCanvas failed to load boundary assets', error)
      })

    return () => {
      disposed = true
      window.removeEventListener('resize', handleResize)
      texture?.dispose()
      renderer.dispose()
      geometry.dispose()
      material.dispose()
      container.innerHTML = ''
    }
  }, [pressures, copPoints, side, showTrajectoryDensity, showTrajectoryFit])

  return <div className="gait-foot__canvas" ref={containerRef} />
}
