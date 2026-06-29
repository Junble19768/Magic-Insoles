export const GAIT_STATES = ['standing', 'walking', 'running'] as const
export type GaitState = (typeof GAIT_STATES)[number]

export const GAIT_CLASSES = ['normal', 'in_toe', 'out_toe'] as const
export type GaitClass = (typeof GAIT_CLASSES)[number]

export interface PressureFrame {
  frameType: number
  seq: number
  pressures: readonly number[]
  leftFoot: readonly number[]
  rightFoot: readonly number[]
  gaitState: GaitState
  mlClass: GaitClass
  mlConf: number
  stepCount: number
  battery: number
}

export interface CopPoint {
  x: number
  y: number
  pressure: number
}

export interface FootCop {
  left: CopPoint
  right: CopPoint
}

export interface ReportData {
  date: string
  reportText: string
  stepCount: number
  gaitSummary: string
  generatedAt: number
}

export interface ReportHistoryItem {
  date: string
  stepCount: number
  gaitSummary: string
  reportText: string
}

export interface ReportHistoryResponse {
  reports: ReportHistoryItem[]
}

export type BleConnectionState = 'disconnected' | 'connecting' | 'connected'

export type FrameListener = (frame: PressureFrame) => void

// ── Activity ──

export interface ActivitySummary {
  date: string
  steps: number
  activeMinutes: number
  distanceKm: number
}

export interface ActivityHistoryDay {
  date: string
  steps: number
}

export interface ActivityHistory {
  days: ActivityHistoryDay[]
}

// ── Gait Analysis ──

export interface FootAnalysis {
  pressures: readonly number[]
  copPoints: readonly CopPoint[]
  classification: GaitClass
  confidence: number
}

export interface GaitSummary {
  date: string
  leftFoot: FootAnalysis
  rightFoot: FootAnalysis
}

// ── GPS ──

export interface GpsPoint {
  timestamp: number
  lat: number
  lng: number
}

export interface GpsRoute {
  date: string
  points: readonly GpsPoint[]
  totalDistanceKm: number
  durationMinutes: number
}

// ── Report (extended) ──

export type ReportPeriod = 'today' | 'week' | 'month'

export interface ReportResponse {
  period: ReportPeriod
  dateRange: { start: string; end: string }
  reportText: string
  stepCount: number
  gaitSummary: string
  generatedAt: number
}

// ── Device Management ──

export interface SavedDeviceInfo {
  deviceId: string
  deviceName: string
  pairedAt: number
  lastConnectedAt: number
}

// ── Balance Assessment ──

export type BalanceGrade = 'excellent' | 'good' | 'fair' | 'needs_improvement'

export type BalanceStatus = 'idle' | 'running' | 'done'

export interface BalanceResult {
  score: number
  grade: BalanceGrade
  leftCopTrajectory: readonly CopPoint[]
  rightCopTrajectory: readonly CopPoint[]
  leftAvgPressures: readonly number[]
  rightAvgPressures: readonly number[]
  swayArea: number
  copStdDev: number
  timestamp: number
}
