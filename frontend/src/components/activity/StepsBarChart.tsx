import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { ActivityHistoryDay } from '@/types'

type ChartVariant = 'compact' | 'full'

interface ChartPadding {
  readonly top: number
  readonly right: number
  readonly bottom: number
  readonly left: number
}

interface ChartConfig {
  readonly height: number
  readonly padding: ChartPadding
  readonly cssClass: string
}

interface ChartLayout {
  readonly gap: number
  readonly barW: number
  readonly chartW: number
  readonly chartH: number
}

interface StepsBarChartProps {
  days: readonly ActivityHistoryDay[]
  variant?: ChartVariant
}

const CHART_CONFIG = {
  full: {
    height: 340,
    padding: { top: 24, right: 16, bottom: 32, left: 48 },
    cssClass: 'chart-canvas chart-canvas--large',
  },
  compact: {
    height: 200,
    padding: { top: 16, right: 12, bottom: 24, left: 40 },
    cssClass: 'chart-canvas',
  },
} as const satisfies Record<ChartVariant, ChartConfig>

function computeBarLayout(
  canvasWidth: number,
  barCount: number,
  padding: ChartPadding,
  chartHeight: number,
): ChartLayout {
  const chartW = canvasWidth - padding.left - padding.right
  const chartH = chartHeight - padding.top - padding.bottom
  const gap = Math.max(4, (chartW / barCount) * 0.35)
  const barW = barCount > 0 ? (chartW - gap * (barCount + 1)) / barCount : 0
  return { gap, barW, chartW, chartH }
}

function drawStepsBarChart(
  canvas: HTMLCanvasElement,
  days: readonly ActivityHistoryDay[],
  maxSteps: number,
  config: ChartConfig,
): boolean {
  const w = canvas.clientWidth
  if (w === 0) return false

  const { height, padding } = config
  const dpr = window.devicePixelRatio || 1
  canvas.width = w * dpr
  canvas.height = height * dpr
  const ctx = canvas.getContext('2d')
  if (!ctx) return false
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  ctx.clearRect(0, 0, w, height)

  const { gap, barW, chartH } = computeBarLayout(w, days.length, padding, height)

  ctx.strokeStyle = '#d7e4de'
  ctx.lineWidth = 1
  ctx.font = '10px system-ui'
  ctx.fillStyle = '#4f6d64'
  ctx.textAlign = 'right'
  const ySteps = 5
  for (let i = 0; i <= ySteps; i += 1) {
    const y = padding.top + (chartH / ySteps) * (ySteps - i)
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(w - padding.right, y)
    ctx.stroke()
    const val = Math.round((maxSteps / ySteps) * i)
    ctx.fillText(val.toLocaleString(), padding.left - 6, y + 4)
  }

  days.forEach((day, index) => {
    const x = padding.left + gap + index * (barW + gap)
    const barH = Math.max(2, (day.steps / maxSteps) * chartH)
    const y = padding.top + chartH - barH

    const gradient = ctx.createLinearGradient(x, y, x, padding.top + chartH)
    gradient.addColorStop(0, '#2F8F78')
    gradient.addColorStop(1, '#163B31')
    ctx.fillStyle = gradient

    const radius = Math.min(4, barW / 2)
    ctx.beginPath()
    ctx.moveTo(x + radius, y)
    ctx.lineTo(x + barW - radius, y)
    ctx.quadraticCurveTo(x + barW, y, x + barW, y + radius)
    ctx.lineTo(x + barW, padding.top + chartH)
    ctx.lineTo(x, padding.top + chartH)
    ctx.lineTo(x, y + radius)
    ctx.quadraticCurveTo(x, y, x + radius, y)
    ctx.closePath()
    ctx.fill()

    ctx.fillStyle = '#4f6d64'
    ctx.textAlign = 'center'
    ctx.fillText(day.date.slice(5), x + barW / 2, padding.top + chartH + 16)
  })

  return true
}

export function StepsBarChart({ days, variant = 'full' }: StepsBarChartProps): ReactElement {
  const config = CHART_CONFIG[variant]
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null)

  const maxSteps = useMemo(() => {
    if (days.length === 0) return 1
    return Math.max(...days.map((d) => d.steps), 1) * 1.15
  }, [days])

  const renderChart = useCallback((): void => {
    const canvas = canvasRef.current
    if (!canvas) return

    const drew = drawStepsBarChart(canvas, days, maxSteps, config)
    if (!drew) {
      requestAnimationFrame(renderChart)
    }
  }, [days, maxSteps, config])

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
    const { gap, barW } = computeBarLayout(rect.width, days.length, config.padding, config.height)
    const index = Math.floor((mx - config.padding.left - gap) / (barW + gap))

    if (index >= 0 && index < days.length) {
      const day = days[index]
      const bx = config.padding.left + gap + index * (barW + gap) + barW / 2
      setTooltip({ x: bx, y: 4, text: `${day.date}  ${day.steps.toLocaleString()} 步` })
    } else {
      setTooltip(null)
    }
  }

  return (
    <div
      ref={containerRef}
      style={{ position: 'relative', marginBottom: '1rem' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setTooltip(null)}
    >
      <canvas ref={canvasRef} className={config.cssClass} height={config.height} />
      {tooltip ? (
        <div className="chart-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
          {tooltip.text}
        </div>
      ) : null}
    </div>
  )
}
