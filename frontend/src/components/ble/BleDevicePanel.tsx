import { useCallback, useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { connect, disconnect, getConnectionState, getSavedDevices, scanAndConnect } from '@/ble/bleService'
import { forgetDevice } from '@/ble/deviceStore'
import { DeviceCard } from '@/components/dashboard/DeviceCard'
import type { BleConnectionState, SavedDeviceInfo } from '@/types'

interface BleDevicePanelProps {
  onConnected?: () => void
  onDisconnected?: () => void
}

export function BleDevicePanel({ onConnected, onDisconnected }: BleDevicePanelProps): ReactElement {
  const [connectionState, setConnectionState] = useState<BleConnectionState>(getConnectionState)
  const [devices, setDevices] = useState<readonly SavedDeviceInfo[]>(getSavedDevices)
  const [scanning, setScanning] = useState(false)

  const refresh = useCallback(() => {
    setConnectionState(getConnectionState())
    setDevices(getSavedDevices())
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const handleConnectFromList = useCallback(async () => {
    setScanning(true)
    try {
      await connect()
      onConnected?.()
    } catch (err) {
      console.error(err)
    } finally {
      setScanning(false)
      refresh()
    }
  }, [onConnected, refresh])

  const handleDisconnect = useCallback(async (_id: string) => {
    await disconnect()
    onDisconnected?.()
    refresh()
  }, [onDisconnected, refresh])

  const handleForget = useCallback((id: string) => {
    forgetDevice(id)
    refresh()
  }, [refresh])

  const handleScan = useCallback(async () => {
    setScanning(true)
    try {
      await scanAndConnect()
      onConnected?.()
    } catch (err) {
      if (err instanceof Error && err.name !== 'NotFoundError') {
        console.error(err)
      }
    } finally {
      setScanning(false)
      refresh()
    }
  }, [onConnected, refresh])

  const isConnected = connectionState === 'connected'

  return (
    <div className="ble-panel">
      <div className="ble-panel__header">
        <h3 className="ble-panel__title">设备管理</h3>
        <button
          type="button"
          className="btn btn--primary btn--sm"
          disabled={scanning || isConnected}
          onClick={handleScan}
        >
          {scanning ? '扫描中...' : '扫描新设备'}
        </button>
      </div>

      {devices.length === 0 ? (
        <p className="state-placeholder">尚无已配对设备，请点击扫描新设备添加</p>
      ) : (
        <div className="ble-panel__list">
          {devices.map((dev) => (
            <DeviceCard
              key={dev.deviceId}
              device={dev}
              isConnected={isConnected}
              onConnect={handleConnectFromList}
              onDisconnect={handleDisconnect}
              onForget={handleForget}
            />
          ))}
        </div>
      )}
    </div>
  )
}
