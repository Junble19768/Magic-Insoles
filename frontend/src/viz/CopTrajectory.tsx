import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import type { CopPoint } from '@/types'

interface CopTrajectoryProps {
  leftCop: CopPoint
  rightCop: CopPoint
}

const WINDOW_MS = 2000
const MAX_POINTS = 100

interface CopHistoryPoint extends CopPoint {
  timestamp: number
}

interface TrajectoryBundle {
  scene: THREE.Scene
  camera: THREE.OrthographicCamera
  renderer: THREE.WebGLRenderer
  leftLine: THREE.Line
  rightLine: THREE.Line
  leftHistory: CopHistoryPoint[]
  rightHistory: CopHistoryPoint[]
}

function createTrajectoryLine(color: number): THREE.Line {
  const geometry = new THREE.BufferGeometry()
  const material = new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity: 0.85,
    linewidth: 2,
  })
  return new THREE.Line(geometry, material)
}

function updateLineGeometry(line: THREE.Line, history: CopHistoryPoint[]): void {
  const positions = new Float32Array(history.length * 3)
  const colors = new Float32Array(history.length * 3)
  const now = Date.now()

  history.forEach((point, index) => {
    const age = now - point.timestamp
    const fade = 1 - age / WINDOW_MS
    const alpha = Math.max(0.1, fade)

    positions[index * 3] = point.x * 0.75
    positions[index * 3 + 1] = point.y * 1.1
    positions[index * 3 + 2] = 0

    colors[index * 3] = alpha
    colors[index * 3 + 1] = alpha * 0.8
    colors[index * 3 + 2] = alpha * 0.4
  })

  line.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  line.geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  ;(line.material as THREE.LineBasicMaterial).vertexColors = true
  line.geometry.attributes.position.needsUpdate = true
  line.geometry.attributes.color.needsUpdate = true
}

function pushHistory(
  history: CopHistoryPoint[],
  point: CopPoint,
  timestamp: number,
): CopHistoryPoint[] {
  const next = [...history, { ...point, timestamp }]
  const cutoff = timestamp - WINDOW_MS
  return next.filter((entry) => entry.timestamp >= cutoff).slice(-MAX_POINTS)
}

export function CopTrajectory({ leftCop, rightCop }: CopTrajectoryProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const bundleRef = useRef<TrajectoryBundle | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) {
      return
    }

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#ffffff')

    const camera = new THREE.OrthographicCamera(-1.2, 1.2, 1.4, -1.4, 0.1, 10)
    camera.position.z = 2

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.setSize(container.clientWidth, container.clientHeight)
    container.appendChild(renderer.domElement)

    const leftLine = createTrajectoryLine(0x1d6b57)
    const rightLine = createTrajectoryLine(0x2f8f78)
    leftLine.position.x = -0.65
    rightLine.position.x = 0.65
    scene.add(leftLine, rightLine)

    bundleRef.current = {
      scene,
      camera,
      renderer,
      leftLine,
      rightLine,
      leftHistory: [],
      rightHistory: [],
    }

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
      leftLine.geometry.dispose()
      rightLine.geometry.dispose()
      ;(leftLine.material as THREE.Material).dispose()
      ;(rightLine.material as THREE.Material).dispose()
      container.innerHTML = ''
      bundleRef.current = null
    }
  }, [])

  useEffect(() => {
    const bundle = bundleRef.current
    if (!bundle) {
      return
    }

    const timestamp = Date.now()
    if (leftCop.pressure > 0) {
      bundle.leftHistory = pushHistory(bundle.leftHistory, leftCop, timestamp)
    }
    if (rightCop.pressure > 0) {
      bundle.rightHistory = pushHistory(bundle.rightHistory, rightCop, timestamp)
    }

    updateLineGeometry(bundle.leftLine, bundle.leftHistory)
    updateLineGeometry(bundle.rightLine, bundle.rightHistory)
    bundle.renderer.render(bundle.scene, bundle.camera)
  }, [leftCop, rightCop])

  return <div className="cop-trajectory" ref={containerRef} />
}
