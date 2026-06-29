import { useEffect, useRef } from 'react'
import type { ReactElement } from 'react'
import type { FootCop } from '@/types'

interface BalanceCopIndicatorProps {
  footCop: FootCop
}

export function BalanceCopIndicator({ footCop }: BalanceCopIndicatorProps): ReactElement {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const dpr = window.devicePixelRatio || 1
    const size = 180
    canvas.width = size * dpr
    canvas.height = size * dpr
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.scale(dpr, dpr)

    ctx.clearRect(0, 0, size, size)

    // Crosshair
    ctx.strokeStyle = '#d7e4de'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(size / 2, 20)
    ctx.lineTo(size / 2, size - 20)
    ctx.moveTo(20, size / 2)
    ctx.lineTo(size - 20, size / 2)
    ctx.stroke()

    // Center point
    ctx.fillStyle = '#2F8F78'
    ctx.beginPath()
    ctx.arc(size / 2, size / 2, 4, 0, Math.PI * 2)
    ctx.fill()

    // Left COP
    const lx = size / 2 + footCop.left.x * 70
    const ly = size / 2 + footCop.left.y * 70
    ctx.fillStyle = '#163B31'
    ctx.beginPath()
    ctx.arc(lx, ly, 5, 0, Math.PI * 2)
    ctx.fill()

    // Right COP
    const rx = size / 2 + footCop.right.x * 70
    const ry = size / 2 + footCop.right.y * 70
    ctx.fillStyle = '#c0392b'
    ctx.beginPath()
    ctx.arc(rx, ry, 5, 0, Math.PI * 2)
    ctx.fill()

    // Label
    ctx.fillStyle = '#4f6d64'
    ctx.font = '10px system-ui'
    ctx.textAlign = 'center'
    ctx.fillText('左脚', lx, ly - 10)
    ctx.fillText('右脚', rx, ry - 10)
  }, [footCop])

  return <canvas ref={canvasRef} className="balance-cop-indicator" width={180} height={180} />
}
