import { useCallback, useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { fetchActivityHistory, fetchActivityToday } from '@/api/client'
import { forgetDevice, getSavedDevices } from '@/ble/deviceStore'
import { getConnectionState } from '@/ble/bleService'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { MiniBarChart } from '@/components/dashboard/MiniBarChart'
import { DeviceCard } from '@/components/dashboard/DeviceCard'
import type { ActivityHistoryDay, ActivitySummary, BleConnectionState, SavedDeviceInfo } from '@/types'

type PageState =
  | { status: 'loading' }
  | { status: 'ready'; summary: ActivitySummary; history: readonly ActivityHistoryDay[] }
  | { status: 'error'; message: string }

export function DashboardPage(): ReactElement {
  const [pageState, setPageState] = useState<PageState>({ status: 'loading' })
  const [savedDevices, setSavedDevices] = useState<readonly SavedDeviceInfo[]>([])
  const [connectionState, setConnectionState] = useState<BleConnectionState>('disconnected')

  useEffect(() => {
    let cancelled = false

    async function load(): Promise<void> {
      try {
        setConnectionState(getConnectionState())

        const [summary, history] = await Promise.all([
          fetchActivityToday(),
          fetchActivityHistory(7),
        ])

        if (cancelled) return

        setSavedDevices(getSavedDevices())
        setPageState({ status: 'ready', summary, history: history.days })
      } catch (error) {
        if (cancelled) return
        setPageState({
          status: 'error',
          message: error instanceof Error ? error.message : '加载数据失败',
        })
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [])

  const handleConnect = useCallback(() => {
    setConnectionState('connecting')
  }, [])

  const handleDisconnect = useCallback(() => {
    setConnectionState('disconnected')
  }, [])

  const handleForget = useCallback((id: string) => {
    forgetDevice(id)
    setSavedDevices(getSavedDevices())
  }, [])

  if (pageState.status === 'loading') {
    return (
      <div className="page">
        <header className="page__header">
          <h1>DashBoard</h1>
          <p>设备概览与关键指标</p>
        </header>
        <div className="metric-grid">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="metric-card skeleton" style={{ height: '5rem' }} />
          ))}
        </div>
      </div>
    )
  }

  if (pageState.status === 'error') {
    return (
      <div className="page">
        <header className="page__header">
          <h1>DashBoard</h1>
        </header>
        <p className="state-placeholder state-placeholder--error">{pageState.message}</p>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="page__header">
        <h1>DashBoard</h1>
        <p>设备概览与关键指标</p>
      </header>

      <div className="metric-grid">
        <MetricCard label="今日步数" value={pageState.summary.steps.toLocaleString()} unit="步" />
        <MetricCard label="有效运动时长" value={pageState.summary.activeMinutes} unit="分钟" />
        <MetricCard label="运动距离" value={pageState.summary.distanceKm} unit="km" />
        <MetricCard label="步态状态" value="正常" />
      </div>

      <div className="dashboard__chart">
        <h3 className="dashboard__section-title">最近 7 天步数</h3>
        <MiniBarChart days={pageState.history} />
      </div>

      <h3 className="dashboard__section-title">设备管理</h3>
      {savedDevices.length === 0 ? (
        <p className="state-placeholder">
          尚无已配对设备。
          <br />
          请使用手机打开本页面，通过底部"更多"菜单进入实时监测或平衡评估页添加设备。
        </p>
      ) : (
        <div className="dashboard__devices">
          {savedDevices.map((dev) => (
            <DeviceCard
              key={dev.deviceId}
              device={dev}
              isConnected={connectionState === 'connected'}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              onForget={handleForget}
            />
          ))}
        </div>
      )}
    </div>
  )
}
