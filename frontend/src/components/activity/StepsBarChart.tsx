import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { ActivityHistoryDay } from '@/types'

interface StepsBarChartProps {
  days: readonly ActivityHistoryDay[]
}

const PADDING = { top: 24, right: 16, bottom: 32, left: 48 }
const HEIGHT = 340

export function StepsBarChart({ days }: StepsBarChartProps): ReactElement {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null)

  const maxSteps = useMemo(() => {
    if (days.length === 0) return 1
    return Math.max(...days.map((d) => d.steps), 1) * 1.15
  }, [days])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const dpr = window.devicePixelRatio || 1
    const w = canvas.clientWidth
    const h = HEIGHT
    canvas.width = w * dpr
    canvas.height = h * dpr
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.scale(dpr, dpr)

    ctx.clearRect(0, 0, w, h)

    const chartW = w - PADDING.left - PADDING.right
    const chartH = h - PADDING.top - PADDING.bottom
    const barCount = days.length
    const gap = Math.max(4, chartW / barCount * 0.35)
    const barW = (chartW - gap * (barCount + 1)) / barCount

    // Y-axis grid + labels
    ctx.strokeStyle = '#d7e4de'
    ctx.lineWidth = 1
    ctx.font = '10px system-ui'
    ctx.fillStyle = '#4f6d64'
    ctx.textAlign = 'right'
    const ySteps = 5
    for (let i = 0; i <= ySteps; i += 1) {
      const y = PADDING.top + (chartH / ySteps) * (ySteps - i)
      ctx.beginPath()
      ctx.moveTo(PADDING.left, y)
      ctx.lineTo(w - PADDING.right, y)
      ctx.stroke()
      const val = Math.round((maxSteps / ySteps) * i)
      ctx.fillText(val.toLocaleString(), PADDING.left - 6, y + 4)
    }

    // Bars
    days.forEach((day, index) => {
      const x = PADDING.left + gap + index * (barW + gap)
      const barH = Math.max(2, (day.steps / maxSteps) * chartH)
      const y = PADDING.top + chartH - barH

      const gradient = ctx.createLinearGradient(x, y, x, PADDING.top + chartH)
      gradient.addColorStop(0, '#2F8F78')
      gradient.addColorStop(1, '#163B31')
      ctx.fillStyle = gradient

      const radius = Math.min(4, barW / 2)
      ctx.beginPath()
      ctx.moveTo(x + radius, y)
      ctx.lineTo(x + barW - radius, y)
      ctx.quadraticCurveTo(x + barW, y, x + barW, y + radius)
      ctx.lineTo(x + barW, PADDING.top + chartH)
      ctx.lineTo(x, PADDING.top + chartH)
      ctx.lineTo(x, y + radius)
      ctx.quadraticCurveTo(x, y, x + radius, y)
      ctx.closePath()
      ctx.fill()

      ctx.fillStyle = '#4f6d64'
      ctx.textAlign = 'center'
      ctx.fillText(day.date.slice(5), x + barW / 2, PADDING.top + chartH + 16)
    })
  }, [days, maxSteps])

  const handleMouseMove = (event: React.MouseEvent): void => {
    const container = containerRef.current
    if (!container || days.length === 0) return

    const rect = container.getBoundingClientRect()
    const mx = event.clientX - rect.left
    const chartW = rect.width - PADDING.left - PADDING.right
    const barCount = days.length
    const gap = Math.max(4, chartW / barCount * 0.35)
    const barW = (chartW - gap * (barCount + 1)) / barCount
    const index = Math.floor((mx - PADDING.left - gap) / (barW + gap))

    if (index >= 0 && index < days.length) {
      const day = days[index]
      const bx = PADDING.left + gap + index * (barW + gap) + barW / 2
      setTooltip({ x: bx, y: 4, text: `${day.date}  ${day.steps.toLocaleString()} 步` })
    } else {
      setTooltip(null)
    }
  }

  return (
    <div ref={containerRef} style={{ position: 'relative', marginBottom: '1rem' }} onMouseMove={handleMouseMove} onMouseLeave={() => setTooltip(null)}>
      <canvas ref={canvasRef} className="chart-canvas chart-canvas--large" height={HEIGHT} />
      {tooltip ? (
        <div className="chart-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
          {tooltip.text}
        </div>
      ) : null}
    </div>
  )
}
