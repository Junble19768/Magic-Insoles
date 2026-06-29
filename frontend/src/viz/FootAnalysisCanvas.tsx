import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { interpolatePressure, pressureToColor } from '@/viz/interpolation'
import { getSensorLayout } from '@/viz/sensorLayout'
import type { CopPoint } from '@/types'

interface FootAnalysisCanvasProps {
  pressures: readonly number[]
  copPoints: readonly CopPoint[]
  side: 'left' | 'right'
}

const GRID_SEGMENTS = 48

export function FootAnalysisCanvas({ pressures, copPoints, side }: FootAnalysisCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color('#f4f7f5')

    const camera = new THREE.OrthographicCamera(-1, 1, 1.5, -1.5, 0.1, 10)
    camera.position.z = 2

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.setSize(container.clientWidth, container.clientHeight)
    container.appendChild(renderer.domElement)

    // Heatmap plane
    const geometry = new THREE.PlaneGeometry(1.6, 2.4, GRID_SEGMENTS, GRID_SEGMENTS)
    const material = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide })
    const mesh = new THREE.Mesh(geometry, material)
    scene.add(mesh)

    // Update heatmap colors
    const positions = geometry.attributes.position
    const colors = new Float32Array(positions.count * 3)
    const layout = getSensorLayout(side)
    for (let i = 0; i < positions.count; i += 1) {
      const x = positions.getX(i) / 0.8
      const y = positions.getY(i) / 1.2
      const p = interpolatePressure(x, y, pressures, layout)
      const [r, g, b] = pressureToColor(p)
      colors[i * 3] = r
      colors[i * 3 + 1] = g
      colors[i * 3 + 2] = b
    }
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geometry.attributes.color.needsUpdate = true

    // COP scatter points
    if (copPoints.length > 0) {
      const copGeom = new THREE.BufferGeometry()
      const copPositions = new Float32Array(copPoints.length * 3)
      copPoints.forEach((pt, i) => {
        copPositions[i * 3] = pt.x * 0.75
        copPositions[i * 3 + 1] = pt.y * 1.1
        copPositions[i * 3 + 2] = 0.01
      })
      copGeom.setAttribute('position', new THREE.BufferAttribute(copPositions, 3))
      const copMat = new THREE.PointsMaterial({ color: 0xc0392b, size: 0.04 })
      const copObj = new THREE.Points(copGeom, copMat)
      scene.add(copObj)
    }

    renderer.render(scene, camera)

    return () => {
      renderer.dispose()
      geometry.dispose()
      material.dispose()
      container.innerHTML = ''
    }
  }, [pressures, copPoints, side])

  return <div className="gait-foot__canvas" ref={containerRef} />
}
