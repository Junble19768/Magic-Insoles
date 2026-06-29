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
