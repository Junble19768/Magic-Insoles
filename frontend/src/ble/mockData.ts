import { FRAME_TYPE_PRESSURE } from '@/ble/frameParser'
import type { GaitClass, GaitState, PressureFrame } from '@/types'

interface MockStreamState {
  timerId: number | null
  seq: number
  phase: number
  stepCount: number
}

const streamState: MockStreamState = {
  timerId: null,
  seq: 0,
  phase: 0,
  stepCount: 0,
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function gaussian(center: number, value: number, spread: number): number {
  const delta = value - center
  return Math.exp(-(delta * delta) / (2 * spread * spread))
}

function buildFootPressures(phase: number, side: 'left' | 'right'): number[] {
  const mirroredPhase = side === 'left' ? phase : phase + Math.PI
  const heelWeight = gaussian(Math.sin(mirroredPhase), 0.2, 0.35)
  const midWeight = gaussian(Math.sin(mirroredPhase + 0.8), 0.55, 0.3)
  const toeWeight = gaussian(Math.sin(mirroredPhase + 1.6), 0.85, 0.28)

  return Array.from({ length: 16 }, (_, index) => {
    const row = Math.floor(index / 4)
    const col = index % 4
    const y = row / 3
    const x = col / 3

    const regionWeight =
      y < 0.34 ? heelWeight : y > 0.66 ? toeWeight : midWeight
    const lateralBias = side === 'left' ? 1 - x * 0.15 : 1 - (1 - x) * 0.15
    const noise = (Math.random() - 0.5) * 18

    return clamp(Math.round(regionWeight * lateralBias * 220 + noise), 0, 255)
  })
}

function resolveGaitClass(phase: number): GaitClass {
  const cycle = (Math.sin(phase * 0.2) + 1) / 2
  if (cycle > 0.82) {
    return 'in_toe'
  }
  if (cycle < 0.18) {
    return 'out_toe'
  }
  return 'normal'
}

function resolveGaitState(pressures: readonly number[]): GaitState {
  const total = pressures.reduce((sum, value) => sum + value, 0)
  if (total < 900) {
    return 'standing'
  }
  if (total > 2600) {
    return 'running'
  }
  return 'walking'
}

/**
 * Create one synthetic BLE pressure frame.
 */
export function createMockFrame(): PressureFrame {
  streamState.phase += 0.22
  streamState.seq = (streamState.seq + 1) % 65536

  if (Math.sin(streamState.phase) > 0.95) {
    streamState.stepCount += 1
  }

  const leftFoot = buildFootPressures(streamState.phase, 'left')
  const rightFoot = buildFootPressures(streamState.phase + Math.PI * 0.5, 'right')
  const pressures = [...leftFoot, ...rightFoot]
  const mlClass = resolveGaitClass(streamState.phase)
  const gaitState = resolveGaitState(pressures)

  return {
    frameType: FRAME_TYPE_PRESSURE,
    seq: streamState.seq,
    pressures,
    leftFoot,
    rightFoot,
    gaitState,
    mlClass,
    mlConf: mlClass === 'normal' ? 0.9 + Math.random() * 0.08 : 0.72 + Math.random() * 0.2,
    stepCount: streamState.stepCount,
    battery: 82,
  }
}

/**
 * Start pushing mock frames at the target interval (default 20ms / 50Hz).
 */
export function startMockStream(
  onFrame: (frame: PressureFrame) => void,
  intervalMs = 20,
): void {
  stopMockStream()
  streamState.timerId = window.setInterval(() => {
    onFrame(createMockFrame())
  }, intervalMs)
}

/**
 * Stop the mock frame stream.
 */
export function stopMockStream(): void {
  if (streamState.timerId !== null) {
    window.clearInterval(streamState.timerId)
    streamState.timerId = null
  }
}

/**
 * Reset mock stream counters for deterministic demos.
 */
export function resetMockStream(): void {
  streamState.seq = 0
  streamState.phase = 0
  streamState.stepCount = 0
}

/* ── Balance Mock Stream ── */

let balanceTimerId: number | null = null

function gaussianNoise(): number {
  let u = 0
  let v = 0
  while (u === 0) u = Math.random()
  while (v === 0) v = Math.random()
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

function buildBalanceFrame(seq: number, swayAmp: number): PressureFrame {
  const lx = gaussianNoise() * swayAmp
  const ly = gaussianNoise() * swayAmp * 0.8
  const rx = gaussianNoise() * swayAmp * 0.9
  const ry = gaussianNoise() * swayAmp * 0.75

  function pressuresForCop(cx: number, cy: number): number[] {
    return Array.from({ length: 16 }, (_, i) => {
      const row = Math.floor(i / 4)
      const col = i % 4
      const sx = col / 3
      const sy = row / 3
      const dist = Math.sqrt((sx - (cx + 1) / 2) ** 2 + (sy - (cy + 1) / 2) ** 2)
      return clamp(Math.round((1 / Math.max(dist, 0.1)) * 45 + (Math.random() - 0.5) * 16), 0, 255)
    })
  }

  const leftFoot = pressuresForCop(lx, ly)
  const rightFoot = pressuresForCop(rx, ry)

  return {
    frameType: FRAME_TYPE_PRESSURE,
    seq: seq % 65536,
    pressures: [...leftFoot, ...rightFoot],
    leftFoot,
    rightFoot,
    gaitState: 'standing',
    mlClass: 'normal',
    mlConf: 0.95,
    stepCount: 0,
    battery: 82,
  }
}

/**
 * Start a 30-second balance mock stream at 50Hz (~1500 frames).
 */
export function startBalanceMockStream(onFrame: (frame: PressureFrame) => void): void {
  stopBalanceMockStream()

  const totalFrames = 1500
  let index = 0

  balanceTimerId = window.setInterval(() => {
    if (index >= totalFrames) {
      stopBalanceMockStream()
      return
    }

    const swayAmp = 0.04 + (index / totalFrames) * 0.04
    onFrame(buildBalanceFrame(index, swayAmp))
    index += 1
  }, 20)
}

/**
 * Stop the balance mock stream.
 */
export function stopBalanceMockStream(): void {
  if (balanceTimerId !== null) {
    window.clearInterval(balanceTimerId)
    balanceTimerId = null
  }
}
