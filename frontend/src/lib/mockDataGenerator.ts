import type {
  ActivityHistory,
  ActivityHistoryDay,
  ActivitySummary,
  BalanceGrade,
  CopPoint,
  FootAnalysis,
  GaitClass,
  GaitSummary,
  GpsPoint,
  GpsRoute,
  PressureFrame,
} from '@/types'
import { FRAME_TYPE_PRESSURE } from '@/ble/frameParser'

/* ── Utilities ── */

function midDays(n: number): Date[] {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(today)
    d.setDate(d.getDate() - (n - 1 - i))
    return d
  })
}

function fmt(date: Date): string {
  return date.toISOString().slice(0, 10)
}

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function gaussian(): number {
  let u = 0
  let v = 0
  while (u === 0) u = Math.random()
  while (v === 0) v = Math.random()
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

/* ── Activity ── */

/**
 * @returns Today's activity summary (steps, active minutes, distance).
 */
export function generateActivityToday(): ActivitySummary {
  const steps = randomInt(5000, 12000)
  return {
    date: fmt(new Date()),
    steps,
    activeMinutes: randomInt(25, 70),
    distanceKm: Math.round(steps * 0.0006 * 100) / 100,
  }
}

/**
 * @returns N-day step count history with realistic weekday/weekend patterns.
 */
export function generateActivityHistory(days: number): ActivityHistory {
  const dates = midDays(days)
  const dayList: ActivityHistoryDay[] = dates.map((date) => {
    const dayOfWeek = date.getDay()
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6
    const base = isWeekend ? randomInt(3000, 7000) : randomInt(6000, 13000)
    return { date: fmt(date), steps: base }
  })
  return { days: dayList }
}

/* ── GPS ── */

/**
 * Olympic Forest Park (Beijing) loop ~5 km.
 */
function olympicParkLoop(): readonly GpsPoint[] {
  const center = { lat: 40.02, lng: 116.39 }
  const radiusLat = 0.012
  const radiusLng = 0.018
  const count = 55
  const now = Date.now()

  return Array.from({ length: count }, (_, index) => {
    const angle = (index / count) * Math.PI * 2
    const lat = center.lat + Math.sin(angle) * radiusLat + gaussian() * 0.0003
    const lng = center.lng + Math.cos(angle) * radiusLng + gaussian() * 0.0004
    return {
      timestamp: now - (count - index) * 45000,
      lat: Math.round(lat * 1e6) / 1e6,
      lng: Math.round(lng * 1e6) / 1e6,
    }
  })
}

/**
 * @returns A synthetic GPS route for today.
 */
export function generateGpsRoute(): GpsRoute {
  const points = olympicParkLoop()
  return {
    date: fmt(new Date()),
    points,
    totalDistanceKm: 5.1,
    durationMinutes: 42,
  }
}

/* ── Gait ── */

function simulateInToeCop(num: number): CopPoint[] {
  const points: CopPoint[] = []
  for (let i = 0; i < num; i += 1) {
    const t = i / num
    points.push({
      x: 0.08 + Math.sin(t * 3.5) * 0.12 + gaussian() * 0.025,
      y: -0.75 + t * 1.5 + gaussian() * 0.03,
      pressure: 1800 + gaussian() * 400,
    })
  }
  return points
}

function simulateNormalCop(num: number): CopPoint[] {
  const points: CopPoint[] = []
  for (let i = 0; i < num; i += 1) {
    const t = i / num
    points.push({
      x: -0.02 + Math.sin(t * 2.8) * 0.06 + gaussian() * 0.02,
      y: -0.75 + t * 1.5 + gaussian() * 0.03,
      pressure: 1850 + gaussian() * 380,
    })
  }
  return points
}

function buildStaticPressures(side: 'left' | 'right', classification: GaitClass): number[] {
  const base = side === 'left'
    ? [180, 120, 40, 5, 200, 160, 80, 10, 220, 190, 60, 15, 100, 70, 30, 5]
    : [175, 115, 35, 5, 195, 155, 75, 10, 215, 185, 55, 15, 95, 65, 25, 5]

  if (classification === 'in_toe') {
    return base.map((v, i) => {
      const col = i % 4
      return clamp(Math.round(v * (col < 2 ? 0.72 : 1.35)), 0, 255)
    })
  }

  return base.map((v) => clamp(Math.round(v + gaussian() * 15), 0, 255))
}

/**
 * @returns A gait summary with one foot slightly in-toe for demo contrast.
 */
export function generateGaitSummary(): GaitSummary {
  return {
    date: fmt(new Date()),
    leftFoot: {
      pressures: buildStaticPressures('left', 'normal'),
      copPoints: simulateNormalCop(100),
      classification: 'normal',
      confidence: 0.94,
    } as FootAnalysis,
    rightFoot: {
      pressures: buildStaticPressures('right', 'in_toe'),
      copPoints: simulateInToeCop(100),
      classification: 'in_toe',
      confidence: 0.78,
    } as FootAnalysis,
  }
}

/* ── Reports ── */

export function generateReportText(period: 'today' | 'week' | 'month'): string {
  const texts: Record<string, string> = {
    today: '宝贝今天活动了 42 分钟，步态整体平稳。建议继续保持户外步行，注意走路时脚尖朝前。今天表现很棒，继续加油！',
    week: '过去一周，宝贝累计步行 21,430 步（日均 3,061 步），整体步态正常，偶有轻度内八（占比约 8%）。周末户外活动时间偏少，建议周末安排 30 分钟以上户外散步，有助于足弓发育和骨骼健康。',
    month: '本月宝贝共完成 96,500 步，日均 3,117 步。步态评估整体良好，内八倾向从上月的 12% 下降至 8%，改善明显。建议继续保持当前运动习惯，注意书包重量和坐姿，帮助维持健康力线发育。',
  }
  return texts[period] ?? texts.today
}

/* ── Balance Mock ── */

function swayPattern(length: number, amplitude: number): CopPoint[] {
  return Array.from({ length }, () => ({
    x: gaussian() * amplitude,
    y: gaussian() * amplitude,
    pressure: 2200 + gaussian() * 300,
  }))
}

/**
 * @returns 30s of balance assessment mock frames (~1500 at 50Hz).
 */
export function generateBalanceMockFrames(): PressureFrame[] {
  const totalFrames = 1500
  const leftCop = swayPattern(totalFrames, 0.08)
  const rightCop = swayPattern(totalFrames, 0.07)

  return Array.from({ length: totalFrames }, (_, index) => {
    const l = leftCop[index]
    const r = rightCop[index]

    const leftPressures = Array.from({ length: 16 }, (_, i) => {
      const row = Math.floor(i / 4)
      const col = i % 4
      const centerX = col / 3
      const centerY = row / 3
      const dist = Math.sqrt((centerX - (l.x + 1) / 2) ** 2 + (centerY - (l.y + 1) / 2) ** 2)
      return clamp(Math.round((1 / Math.max(dist, 0.1)) * 45 + gaussian() * 8), 0, 255)
    })

    const rightPressures = Array.from({ length: 16 }, (_, i) => {
      const row = Math.floor(i / 4)
      const col = i % 4
      const centerX = col / 3
      const centerY = row / 3
      const dist = Math.sqrt((centerX - (r.x + 1) / 2) ** 2 + (centerY - (r.y + 1) / 2) ** 2)
      return clamp(Math.round((1 / Math.max(dist, 0.1)) * 45 + gaussian() * 8), 0, 255)
    })

    return {
      frameType: FRAME_TYPE_PRESSURE,
      seq: index % 65536,
      pressures: [...leftPressures, ...rightPressures],
      leftFoot: leftPressures,
      rightFoot: rightPressures,
      gaitState: 'standing',
      mlClass: 'normal',
      mlConf: 0.95,
      stepCount: 0,
      battery: 82,
    }
  })
}

/* ── Score helper ── */

/**
 * @returns A realistic balance score with deterministic seed for testing.
 */
export function calculateMockBalanceScore(): { score: number; grade: BalanceGrade } {
  const score = clamp(Math.round(85 + gaussian() * 8), 40, 100)
  let grade: BalanceGrade = 'good'
  if (score >= 85) grade = 'excellent'
  else if (score >= 70) grade = 'good'
  else if (score >= 55) grade = 'fair'
  else grade = 'needs_improvement'
  return { score, grade }
}
