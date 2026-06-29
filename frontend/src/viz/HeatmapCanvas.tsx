import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { interpolatePressure, pressureToColor } from '@/viz/interpolation'
import { getSensorLayout } from '@/viz/sensorLayout'

interface HeatmapCanvasProps {
  leftFoot: readonly number[]
  rightFoot: readonly number[]
}

const GRID_SEGMENTS = 48

interface SceneBundle {
  scene: THREE.Scene
  camera: THREE.OrthographicCamera
  renderer: THREE.WebGLRenderer
  leftMesh: THREE.Mesh
  rightMesh: THREE.Mesh
}

function createFootMesh(side: 'left' | 'right', offsetX: number): THREE.Mesh {
  const geometry = new THREE.PlaneGeometry(1.6, 2.4, GRID_SEGMENTS, GRID_SEGMENTS)
  const material = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide })
  const mesh = new THREE.Mesh(geometry, material)
  mesh.position.set(offsetX, 0, 0)
  mesh.userData.side = side
  return mesh
}

function updateFootColors(mesh: THREE.Mesh, pressures: readonly number[]): void {
  const geometry = mesh.geometry as THREE.PlaneGeometry
  const positions = geometry.attributes.position
  const colors = new Float32Array(positions.count * 3)
  const side = mesh.userData.side as 'left' | 'right'
  const layout = getSensorLayout(side)

  for (let index = 0; index < positions.count; index += 1) {
    const x = positions.getX(index)
    const y = positions.getY(index)
    const normalizedX = x / 0.8
    const normalizedY = y / 1.2
    const pressure = interpolatePressure(normalizedX, normalizedY, pressures, layout)
    const [red, green, blue] = pressureToColor(pressure)

    colors[index * 3] = red
    colors[index * 3 + 1] = green
    colors[index * 3 + 2] = blue
  }

  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  geometry.attributes.color.needsUpdate = true
}

export function HeatmapCanvas({ leftFoot, rightFoot }: HeatmapCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const bundleRef = useRef<SceneBundle | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return
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
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
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

    updateFootColors(bundle.leftMesh, leftFoot)
    updateFootColors(bundle.rightMesh, rightFoot)
    bundle.renderer.render(bundle.scene, bundle.camera)
  }, [leftFoot, rightFoot])

  return <div className="heatmap-canvas" ref={containerRef} />
}
