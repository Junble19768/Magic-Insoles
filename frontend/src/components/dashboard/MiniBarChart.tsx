import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { ActivityHistoryDay } from '@/types'

interface MiniBarChartProps {
  days: readonly ActivityHistoryDay[]
}

const BAR_GAP = 8
const BAR_MAX_HEIGHT = 100
const HEIGHT = 160
const PADDING = { left: 16, right: 16, bottom: 20 } as const

interface ChartLayout {
  barWidth: number
}

function computeLayout(canvasWidth: number, barCount: number): ChartLayout {
  const chartWidth = Math.max(0, canvasWidth - PADDING.left - PADDING.right)
  const barWidth =
    barCount > 0 ? (chartWidth - BAR_GAP * (barCount - 1)) / barCount : 8
  return { barWidth }
}

function drawMiniBarChart(
  canvas: HTMLCanvasElement,
  days: readonly ActivityHistoryDay[],
  maxSteps: number,
): boolean {
  const w = canvas.clientWidth
  if (w === 0) return false

  const dpr = window.devicePixelRatio || 1
  canvas.width = w * dpr
  canvas.height = HEIGHT * dpr
  const ctx = canvas.getContext('2d')
  if (!ctx) return false
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  ctx.clearRect(0, 0, w, HEIGHT)

  const { barWidth } = computeLayout(w, days.length)

  days.forEach((day, index) => {
    const x = PADDING.left + index * (barWidth + BAR_GAP)
    const barH = Math.max(4, (day.steps / maxSteps) * BAR_MAX_HEIGHT)
    const y = HEIGHT - barH - PADDING.bottom

    const gradient = ctx.createLinearGradient(x, y, x, HEIGHT - PADDING.bottom)
    gradient.addColorStop(0, '#2F8F78')
    gradient.addColorStop(1, '#163B31')
    ctx.fillStyle = gradient

    const radius = Math.min(4, barWidth / 2)
    ctx.beginPath()
    ctx.moveTo(x + radius, y)
    ctx.lineTo(x + barWidth - radius, y)
    ctx.quadraticCurveTo(x + barWidth, y, x + barWidth, y + radius)
    ctx.lineTo(x + barWidth, HEIGHT - PADDING.bottom)
    ctx.lineTo(x, HEIGHT - PADDING.bottom)
    ctx.lineTo(x, y + radius)
    ctx.quadraticCurveTo(x, y, x + radius, y)
    ctx.closePath()
    ctx.fill()

    ctx.fillStyle = '#4f6d64'
    ctx.font = '10px system-ui'
    ctx.textAlign = 'center'
    ctx.fillText(day.date.slice(5), x + barWidth / 2, HEIGHT - 4)
  })

  return true
}

export function MiniBarChart({ days }: MiniBarChartProps): ReactElement {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null)

  const maxSteps = useMemo(() => {
    if (days.length === 0) return 1
    return Math.max(...days.map((d) => d.steps), 1)
  }, [days])

  const renderChart = useCallback((): void => {
    const canvas = canvasRef.current
    if (!canvas) return

    const drew = drawMiniBarChart(canvas, days, maxSteps)
    if (!drew) {
      requestAnimationFrame(renderChart)
    }
  }, [days, maxSteps])

  useEffect(() => {
    renderChart()

    const container = containerRef.current
    if (!container) return

    const observer = new ResizeObserver(() => {
      renderChart()
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
    }
  }, [renderChart])

  const handleMouseMove = (event: React.MouseEvent): void => {
    const container = containerRef.current
    if (!container || days.length === 0) return

    const rect = container.getBoundingClientRect()
    const mx = event.clientX - rect.left
    const { barWidth } = computeLayout(rect.width, days.length)
    const barIndex = Math.floor((mx - PADDING.left) / (barWidth + BAR_GAP))

    if (barIndex >= 0 && barIndex < days.length) {
      const day = days[barIndex]
      const bx = PADDING.left + barIndex * (barWidth + BAR_GAP) + barWidth / 2
      setTooltip({
        x: bx,
        y: 8,
        text: `${day.date}  ${day.steps.toLocaleString()} 步`,
      })
    } else {
      setTooltip(null)
    }
  }

  return (
    <div
      ref={containerRef}
      style={{ position: 'relative' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setTooltip(null)}
    >
      <canvas ref={canvasRef} className="chart-canvas" height={HEIGHT} />
      {tooltip ? (
        <div className="chart-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
          {tooltip.text}
        </div>
      ) : null}
    </div>
  )
}
