import type { ReactElement } from 'react'
import type { SavedDeviceInfo } from '@/types'

interface DeviceCardProps {
  device: SavedDeviceInfo
  isConnected: boolean
  battery?: number
  onConnect: (id: string) => void
  onDisconnect: (id: string) => void
  onForget: (id: string) => void
}

export function DeviceCard({
  device,
  isConnected,
  battery,
  onConnect,
  onDisconnect,
  onForget,
}: DeviceCardProps): ReactElement {
  const lastConnected = new Date(device.lastConnectedAt).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div className="device-card">
      <div className="device-card__info">
        <span className="device-card__name">{device.deviceName}</span>
        <span className="device-card__meta">上次连接 {lastConnected}</span>
        {battery !== undefined ? (
          <span className="device-card__battery">电量 {battery}%</span>
        ) : null}
        <span
          className={`device-card__status ${
            isConnected ? 'device-card__status--connected' : 'device-card__status--disconnected'
          }`}
        >
          {isConnected ? '已连接' : '未连接'}
        </span>
      </div>
      <div className="device-card__actions">
        {isConnected ? (
          <button type="button" className="btn btn--outline btn--sm" onClick={() => onDisconnect(device.deviceId)}>
            断开
          </button>
        ) : (
          <button type="button" className="btn btn--primary btn--sm" onClick={() => onConnect(device.deviceId)}>
            连接
          </button>
        )}
        <button type="button" className="btn btn--danger btn--sm" onClick={() => onForget(device.deviceId)}>
          忘记
        </button>
      </div>
    </div>
  )
}
