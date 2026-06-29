import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { ActivityHistoryDay } from '@/types'

interface MiniBarChartProps {
  days: readonly ActivityHistoryDay[]
}

const BAR_GAP = 8
const BAR_MAX_HEIGHT = 100
const HEIGHT = 160

export function MiniBarChart({ days }: MiniBarChartProps): ReactElement {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null)

  const maxSteps = useMemo(() => {
    if (days.length === 0) return 1
    return Math.max(...days.map((d) => d.steps), 1)
  }, [days])
  const barWidth = days.length > 0 ? (200 - BAR_GAP * (days.length - 1)) / days.length : 8

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = canvas.clientWidth * dpr
    canvas.height = HEIGHT * dpr
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.scale(dpr, dpr)

    ctx.clearRect(0, 0, canvas.clientWidth, HEIGHT)

    days.forEach((day, index) => {
      const x = index * (barWidth + BAR_GAP) + 16
      const barH = Math.max(4, (day.steps / maxSteps) * BAR_MAX_HEIGHT)
      const y = HEIGHT - barH - 20

      const gradient = ctx.createLinearGradient(x, y, x, HEIGHT - 20)
      gradient.addColorStop(0, '#2F8F78')
      gradient.addColorStop(1, '#163B31')
      ctx.fillStyle = gradient

      const radius = Math.min(4, barWidth / 2)
      ctx.beginPath()
      ctx.moveTo(x + radius, y)
      ctx.lineTo(x + barWidth - radius, y)
      ctx.quadraticCurveTo(x + barWidth, y, x + barWidth, y + radius)
      ctx.lineTo(x + barWidth, HEIGHT - 20)
      ctx.lineTo(x, HEIGHT - 20)
      ctx.lineTo(x, y + radius)
      ctx.quadraticCurveTo(x, y, x + radius, y)
      ctx.closePath()
      ctx.fill()

      ctx.fillStyle = '#4f6d64'
      ctx.font = '10px system-ui'
      ctx.textAlign = 'center'
      ctx.fillText(day.date.slice(5), x + barWidth / 2, HEIGHT - 4)
    })
  }, [days, maxSteps, barWidth])

  const handleMouseMove = (event: React.MouseEvent): void => {
    const container = containerRef.current
    if (!container || days.length === 0) return

    const rect = container.getBoundingClientRect()
    const mx = event.clientX - rect.left
    const barIndex = Math.floor((mx - 16) / (barWidth + BAR_GAP))

    if (barIndex >= 0 && barIndex < days.length) {
      const day = days[barIndex]
      const bx = barIndex * (barWidth + BAR_GAP) + 16 + barWidth / 2
      setTooltip({
        x: bx + 16,
        y: 8,
        text: `${day.date}  ${day.steps.toLocaleString()} 步`,
      })
    } else {
      setTooltip(null)
    }
  }

  return (
    <div ref={containerRef} style={{ position: 'relative' }} onMouseMove={handleMouseMove} onMouseLeave={() => setTooltip(null)}>
      <canvas ref={canvasRef} className="chart-canvas" height={HEIGHT} />
      {tooltip ? (
        <div className="chart-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
          {tooltip.text}
        </div>
      ) : null}
    </div>
  )
}
