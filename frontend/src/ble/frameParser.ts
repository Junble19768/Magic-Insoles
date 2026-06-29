import type { GaitClass, GaitState, PressureFrame } from '@/types'

export const FRAME_TYPE_PRESSURE = 0x01
export const FRAME_BYTE_LENGTH = 41

const GAIT_STATE_MAP: readonly GaitState[] = ['standing', 'walking', 'running']
const GAIT_CLASS_MAP: readonly GaitClass[] = ['normal', 'in_toe', 'out_toe']

/**
 * Parse a BLE pressure frame from binary payload.
 */
export function parseInsoleFrame(dataView: DataView): PressureFrame | null {
  if (dataView.byteLength < FRAME_BYTE_LENGTH) {
    return null
  }

  const frameType = dataView.getUint8(0)
  if (frameType !== FRAME_TYPE_PRESSURE) {
    return null
  }

  const pressures = Array.from({ length: 32 }, (_, index) => dataView.getUint8(3 + index))
  const gaitStateRaw = dataView.getUint8(35)
  const mlClassRaw = dataView.getUint8(36)

  return {
    frameType,
    seq: dataView.getUint16(1, true),
    pressures,
    leftFoot: pressures.slice(0, 16),
    rightFoot: pressures.slice(16, 32),
    gaitState: GAIT_STATE_MAP[gaitStateRaw] ?? 'standing',
    mlClass: GAIT_CLASS_MAP[mlClassRaw] ?? 'normal',
    mlConf: dataView.getUint8(37) / 100,
    stepCount: dataView.getUint16(38, true),
    battery: dataView.getUint8(40),
  }
}

/**
 * Encode a pressure frame for mock data and parser self-tests.
 */
export function encodeInsoleFrame(frame: Omit<PressureFrame, 'leftFoot' | 'rightFoot'>): ArrayBuffer {
  const buffer = new ArrayBuffer(FRAME_BYTE_LENGTH)
  const view = new DataView(buffer)

  view.setUint8(0, frame.frameType)
  view.setUint16(1, frame.seq, true)

  frame.pressures.forEach((value, index) => {
    view.setUint8(3 + index, Math.max(0, Math.min(255, Math.round(value))))
  })

  const gaitStateIndex = GAIT_STATE_MAP.indexOf(frame.gaitState)
  const mlClassIndex = GAIT_CLASS_MAP.indexOf(frame.mlClass)

  view.setUint8(35, gaitStateIndex >= 0 ? gaitStateIndex : 0)
  view.setUint8(36, mlClassIndex >= 0 ? mlClassIndex : 0)
  view.setUint8(37, Math.max(0, Math.min(100, Math.round(frame.mlConf * 100))))
  view.setUint16(38, frame.stepCount, true)
  view.setUint8(40, frame.battery)

  return buffer
}

/**
 * Lightweight round-trip validation for parser correctness.
 */
export function runFrameParserSelfTest(): boolean {
  const sample: Omit<PressureFrame, 'leftFoot' | 'rightFoot'> = {
    frameType: FRAME_TYPE_PRESSURE,
    seq: 1024,
    pressures: Array.from({ length: 32 }, (_, index) => (index * 7) % 256),
    gaitState: 'walking',
    mlClass: 'in_toe',
    mlConf: 0.87,
    stepCount: 321,
    battery: 76,
  }

  const parsed = parseInsoleFrame(new DataView(encodeInsoleFrame(sample)))
  if (!parsed) {
    return false
  }

  return (
    parsed.seq === sample.seq &&
    parsed.gaitState === sample.gaitState &&
    parsed.mlClass === sample.mlClass &&
    parsed.mlConf === 0.87 &&
    parsed.stepCount === sample.stepCount &&
    parsed.battery === sample.battery &&
    parsed.pressures.every((value, index) => value === sample.pressures[index])
  )
}
