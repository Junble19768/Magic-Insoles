import { describe, expect, it } from 'vitest'
import { encodeInsoleFrame, FRAME_BYTE_LENGTH, FRAME_TYPE_PRESSURE, parseInsoleFrame, runFrameParserSelfTest } from '@/ble/frameParser'
import type { PressureFrame } from '@/types'

describe('parseInsoleFrame', () => {
  function makeFrame(overrides: Partial<PressureFrame> = {}): ArrayBuffer {
    const defaults: Omit<PressureFrame, 'leftFoot' | 'rightFoot'> = {
      frameType: FRAME_TYPE_PRESSURE,
      seq: 42,
      pressures: Array.from({ length: 32 }, (_, i) => (i * 8) % 256),
      gaitState: 'walking',
      mlClass: 'normal',
      mlConf: 0.88,
      stepCount: 999,
      battery: 78,
      ...overrides,
    }
    return encodeInsoleFrame(defaults)
  }

  it('parses a valid 41-byte pressure frame', () => {
    const result = parseInsoleFrame(new DataView(makeFrame()))
    expect(result).not.toBeNull()
    expect(result!.frameType).toBe(FRAME_TYPE_PRESSURE)
    expect(result!.seq).toBe(42)
    expect(result!.pressures).toHaveLength(32)
    expect(result!.leftFoot).toHaveLength(16)
    expect(result!.rightFoot).toHaveLength(16)
    expect(result!.gaitState).toBe('walking')
    expect(result!.mlClass).toBe('normal')
    expect(result!.mlConf).toBe(0.88)
    expect(result!.stepCount).toBe(999)
    expect(result!.battery).toBe(78)
  })

  it('returns null for wrong frame type', () => {
    const buf = makeFrame({ frameType: 0xff })
    expect(parseInsoleFrame(new DataView(buf))).toBeNull()
  })

  it('returns null for data shorter than 41 bytes', () => {
    const short = new ArrayBuffer(20)
    expect(parseInsoleFrame(new DataView(short))).toBeNull()
  })

  it('splits left and right foot correctly (0-15 vs 16-31)', () => {
    const pressures = Array.from({ length: 32 }, (_, i) => i)
    const buf = makeFrame({ pressures })
    const result = parseInsoleFrame(new DataView(buf))
    expect(result!.leftFoot).toEqual(pressures.slice(0, 16))
    expect(result!.rightFoot).toEqual(pressures.slice(16, 32))
  })

  it('scales mlConf from 0-100 to 0.0-1.0', () => {
    const buf = makeFrame({ mlConf: 0.75 })
    const result = parseInsoleFrame(new DataView(buf))
    expect(result!.mlConf).toBe(0.75)
  })

  it('handles zero pressures', () => {
    const buf = makeFrame({ pressures: new Array(32).fill(0) })
    const result = parseInsoleFrame(new DataView(buf))
    expect(result!.pressures.every((v) => v === 0)).toBe(true)
  })

  it('handles max pressures (255)', () => {
    const buf = makeFrame({ pressures: new Array(32).fill(255) })
    const result = parseInsoleFrame(new DataView(buf))
    expect(result!.pressures.every((v) => v === 255)).toBe(true)
  })

  it('self-test returns true', () => {
    expect(runFrameParserSelfTest()).toBe(true)
  })

  it('round-trips 100 frames correctly', () => {
    for (let i = 0; i < 100; i += 1) {
      const buf = makeFrame({ seq: i, mlConf: Math.random() })
      const parsed = parseInsoleFrame(new DataView(buf))
      expect(parsed).not.toBeNull()
      expect(parsed!.seq).toBe(i)
    }
  })
})

describe('encodeInsoleFrame', () => {
  it('produces exactly 41 bytes', () => {
    const buf = encodeInsoleFrame({
      frameType: FRAME_TYPE_PRESSURE,
      seq: 0,
      pressures: new Array(32).fill(0),
      gaitState: 'standing',
      mlClass: 'normal',
      mlConf: 0.5,
      stepCount: 0,
      battery: 50,
    })
    expect(buf.byteLength).toBe(FRAME_BYTE_LENGTH)
  })

  it('clamps mlConf to 0-100 range in bytes', () => {
    const buf = encodeInsoleFrame({
      frameType: FRAME_TYPE_PRESSURE,
      seq: 0,
      pressures: new Array(32).fill(0),
      gaitState: 'standing',
      mlClass: 'normal',
      mlConf: 1.5,
      stepCount: 0,
      battery: 50,
    })
    const view = new DataView(buf)
    expect(view.getUint8(37)).toBe(100)
  })
})
