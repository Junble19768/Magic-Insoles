import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import {
  buildBoundaryFootHeatmap,
  fieldToImageData,
  loadBoundaryAssets,
} from '@/viz/boundary'

interface HeatmapCanvasProps {
  leftFoot: readonly number[]
  rightFoot: readonly number[]
}

interface SceneBundle {
  scene: THREE.Scene
  camera: THREE.OrthographicCamera
  renderer: THREE.WebGLRenderer
  leftMesh: THREE.Mesh
  rightMesh: THREE.Mesh
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

function updateFootTexture(
  mesh: THREE.Mesh,
  pressures: readonly number[],
  side: 'left' | 'right',
): void {
  const assets = mesh.userData.boundaryAssets
  if (!assets) {
    return
  }

  const heatmap = buildBoundaryFootHeatmap(assets, pressures, side)
  const image = fieldToImageData(
    heatmap.field,
    heatmap.displayWidth,
    heatmap.displayHeight,
    heatmap.peak,
  )

  const oldTexture = mesh.userData.texture as THREE.DataTexture | undefined
  oldTexture?.dispose()

  const texture = imageDataToTexture(image)
  mesh.userData.texture = texture
  ;(mesh.material as THREE.MeshBasicMaterial).map = texture
  ;(mesh.material as THREE.MeshBasicMaterial).needsUpdate = true
}

function createFootMesh(side: 'left' | 'right', offsetX: number): THREE.Mesh {
  const geometry = new THREE.PlaneGeometry(0.9, 1.35)
  const material = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide })
  const mesh = new THREE.Mesh(geometry, material)
  mesh.position.set(offsetX, 0, 0)
  mesh.userData.side = side
  return mesh
}

export function HeatmapCanvas({ leftFoot, rightFoot }: HeatmapCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const bundleRef = useRef<SceneBundle | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return undefined
    }

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#f4f7f5')

    const camera = new THREE.OrthographicCamera(-2.2, 2.2, 1.8, -1.8, 0.1, 10)
    camera.position.z = 2

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.setSize(container.clientWidth, container.clientHeight)
    container.appendChild(renderer.domElement)

    const leftMesh = createFootMesh('left', -1.1)
    const rightMesh = createFootMesh('right', 1.1)
    scene.add(leftMesh, rightMesh)

    bundleRef.current = { scene, camera, renderer, leftMesh, rightMesh }

    const handleResize = (): void => {
      const bundle = bundleRef.current
      if (!bundle) {
        return
      }
      bundle.renderer.setSize(container.clientWidth, container.clientHeight)
      bundle.camera.updateProjectionMatrix()
      bundle.renderer.render(bundle.scene, bundle.camera)
    }

    window.addEventListener('resize', handleResize)

    void loadBoundaryAssets().then((assets) => {
      leftMesh.userData.boundaryAssets = assets
      rightMesh.userData.boundaryAssets = assets
      updateFootTexture(leftMesh, leftFoot, 'left')
      updateFootTexture(rightMesh, rightFoot, 'right')
      renderer.render(scene, camera)
    })

    return () => {
      window.removeEventListener('resize', handleResize)
      const leftTexture = leftMesh.userData.texture as THREE.DataTexture | undefined
      const rightTexture = rightMesh.userData.texture as THREE.DataTexture | undefined
      leftTexture?.dispose()
      rightTexture?.dispose()
      renderer.dispose()
      leftMesh.geometry.dispose()
      rightMesh.geometry.dispose()
      ;(leftMesh.material as THREE.Material).dispose()
      ;(rightMesh.material as THREE.Material).dispose()
      container.innerHTML = ''
      bundleRef.current = null
    }
  }, [])

  useEffect(() => {
    const bundle = bundleRef.current
    if (!bundle) {
      return
    }
    if (!bundle.leftMesh.userData.boundaryAssets) {
      return
    }

    updateFootTexture(bundle.leftMesh, leftFoot, 'left')
    updateFootTexture(bundle.rightMesh, rightFoot, 'right')
    bundle.renderer.render(bundle.scene, bundle.camera)
  }, [leftFoot, rightFoot])

  return <div className="heatmap-canvas" ref={containerRef} />
}
