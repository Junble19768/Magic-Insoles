import type { BleConnectionState } from '@/types'

interface BleConnectButtonProps {
  connectionState: BleConnectionState
  onConnect: () => void
  onDisconnect: () => void
}

const STATE_LABEL: Record<BleConnectionState, string> = {
  disconnected: '未连接',
  connecting: '连接中…',
  connected: '已连接',
}

export function BleConnectButton({
  connectionState,
  onConnect,
  onDisconnect,
}: BleConnectButtonProps) {
  const isConnected = connectionState === 'connected'
  const isConnecting = connectionState === 'connecting'

  return (
    <div className="ble-connect">
      <span className={`ble-connect__status ble-connect__status--${connectionState}`}>
        {STATE_LABEL[connectionState]}
      </span>
      <button
        type="button"
        className="ble-connect__button"
        disabled={isConnecting}
        onClick={isConnected ? onDisconnect : onConnect}
      >
        {isConnected ? '断开' : isConnecting ? '连接中' : '连接设备'}
      </button>
    </div>
  )
}
