import { parseInsoleFrame } from '@/ble/frameParser'
import { resetMockStream, startMockStream, stopMockStream } from '@/ble/mockData'
import type { BleConnectionState, FrameListener, PressureFrame } from '@/types'

const SERVICE_UUID = '0000fff0-0000-1000-8000-00805f9b34fb'
const CHARACTERISTIC_UUID = '0000fff1-0000-1000-8000-00805f9b34fb'

interface BleServiceState {
  connectionState: BleConnectionState
  listeners: Set<FrameListener>
  useMock: boolean
  device: BluetoothDevice | null
  characteristic: BluetoothRemoteGATTCharacteristic | null
}

const state: BleServiceState = {
  connectionState: 'disconnected',
  listeners: new Set(),
  useMock: true,
  device: null,
  characteristic: null,
}

function setConnectionState(next: BleConnectionState): void {
  state.connectionState = next
}

function notifyListeners(frame: PressureFrame): void {
  state.listeners.forEach((listener) => listener(frame))
}

function handleCharacteristicValue(event: Event): void {
  const target = event.target as BluetoothRemoteGATTCharacteristic
  const value = target.value
  if (!value) {
    return
  }

  const frame = parseInsoleFrame(value)
  if (frame) {
    notifyListeners(frame)
  }
}

async function connectRealDevice(): Promise<void> {
  if (!navigator.bluetooth) {
    throw new Error('Web Bluetooth is not available in this browser.')
  }

  setConnectionState('connecting')

  const device = await navigator.bluetooth.requestDevice({
    filters: [{ services: [SERVICE_UUID] }],
    optionalServices: [SERVICE_UUID],
  })

  device.addEventListener('gattserverdisconnected', () => {
    state.device = null
    state.characteristic = null
    setConnectionState('disconnected')
  })

  const server = await device.gatt?.connect()
  if (!server) {
    throw new Error('Failed to connect to GATT server.')
  }

  const service = await server.getPrimaryService(SERVICE_UUID)
  const characteristic = await service.getCharacteristic(CHARACTERISTIC_UUID)

  characteristic.addEventListener('characteristicvaluechanged', handleCharacteristicValue)
  await characteristic.startNotifications()

  state.device = device
  state.characteristic = characteristic
  setConnectionState('connected')
}

/**
 * Subscribe to parsed pressure frames.
 */
export function subscribeFrames(listener: FrameListener): () => void {
  state.listeners.add(listener)
  return () => {
    state.listeners.delete(listener)
  }
}

/**
 * Get current BLE connection state.
 */
export function getConnectionState(): BleConnectionState {
  return state.connectionState
}

/**
 * Toggle mock mode for development without hardware.
 */
export function setUseMock(useMock: boolean): void {
  state.useMock = useMock
}

/**
 * Connect to mock stream or real BLE device.
 */
export async function connect(): Promise<void> {
  if (state.connectionState === 'connected' || state.connectionState === 'connecting') {
    return
  }

  if (state.useMock) {
    setConnectionState('connecting')
    resetMockStream()
    startMockStream(notifyListeners, 20)
    setConnectionState('connected')
    return
  }

  await connectRealDevice()
}

/**
 * Disconnect from mock stream or BLE device.
 */
export async function disconnect(): Promise<void> {
  if (state.useMock) {
    stopMockStream()
    setConnectionState('disconnected')
    return
  }

  if (state.characteristic) {
    state.characteristic.removeEventListener(
      'characteristicvaluechanged',
      handleCharacteristicValue,
    )
    state.characteristic = null
  }

  if (state.device?.gatt?.connected) {
    state.device.gatt.disconnect()
  }

  state.device = null
  setConnectionState('disconnected')
}
