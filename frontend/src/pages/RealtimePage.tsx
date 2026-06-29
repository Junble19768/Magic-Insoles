import { useCallback, useEffect, useState } from 'react'
import {
  connect,
  disconnect,
  getConnectionState,
  subscribeFrames,
} from '@/ble/bleService'
import { runFrameParserSelfTest } from '@/ble/frameParser'
import { BleConnectButton } from '@/components/BleConnectButton'
import { GaitStatusBar } from '@/components/GaitStatusBar'
import { calculateCop } from '@/viz/cop'
import { CopTrajectory } from '@/viz/CopTrajectory'
import { HeatmapCanvas } from '@/viz/HeatmapCanvas'
import type { BleConnectionState, PressureFrame } from '@/types'

const EMPTY_PRESSURES = Array.from({ length: 16 }, () => 0)

export function RealtimePage() {
  const [connectionState, setConnectionState] = useState<BleConnectionState>(
    getConnectionState(),
  )
  const [frame, setFrame] = useState<PressureFrame | null>(null)
  const [abnormalStreak, setAbnormalStreak] = useState(0)

  useEffect(() => {
    if (!runFrameParserSelfTest()) {
      console.error('BLE frame parser self-test failed.')
    }
  }, [])

  useEffect(() => {
    return subscribeFrames((nextFrame) => {
      setFrame(nextFrame)
      setAbnormalStreak((current) =>
        nextFrame.mlClass === 'normal' ? 0 : current + 1,
      )
    })
  }, [])

  const handleConnect = useCallback(async () => {
    try {
      await connect()
      setConnectionState(getConnectionState())
    } catch (error) {
      console.error(error)
      setConnectionState('disconnected')
    }
  }, [])

  const handleDisconnect = useCallback(async () => {
    await disconnect()
    setConnectionState(getConnectionState())
    setFrame(null)
    setAbnormalStreak(0)
  }, [])

  const leftFoot = frame?.leftFoot ?? EMPTY_PRESSURES
  const rightFoot = frame?.rightFoot ?? EMPTY_PRESSURES
  const leftCop = calculateCop(leftFoot, 'left')
  const rightCop = calculateCop(rightFoot, 'right')

  return (
    <div className="page realtime-page">
      <header className="page__header">
        <h1>实时监测</h1>
        <p>BLE 近程可视化（开发模式使用模拟数据）</p>
      </header>

      <BleConnectButton
        connectionState={connectionState}
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
      />

      <HeatmapCanvas leftFoot={leftFoot} rightFoot={rightFoot} />

      <section className="realtime-page__cop">
        <h2>COP 轨迹</h2>
        <CopTrajectory leftCop={leftCop} rightCop={rightCop} />
      </section>

      <GaitStatusBar frame={frame} abnormalStreak={abnormalStreak} />
    </div>
  )
}
