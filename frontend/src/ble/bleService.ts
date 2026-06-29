import { parseInsoleFrame } from '@/ble/frameParser'
import { resetMockStream, startBalanceMockStream, startMockStream, stopMockStream } from '@/ble/mockData'
import { findDevice, forgetDevice as removeDevice, getSavedDevices, saveDevice, updateLastConnected } from '@/ble/deviceStore'
import type { BleConnectionState, FrameListener, PressureFrame, SavedDeviceInfo } from '@/types'

const SERVICE_UUID = '0000fff0-0000-1000-8000-00805f9b34fb'
const NOTIFY_CHAR_UUID = '0000fff1-0000-1000-8000-00805f9b34fb'
const WRITE_CHAR_UUID = '0000fff2-0000-1000-8000-00805f9b34fb'

interface BleServiceState {
  connectionState: BleConnectionState
  listeners: Set<FrameListener>
  useMock: boolean
  device: BluetoothDevice | null
  writeCharacteristic: BluetoothRemoteGATTCharacteristic | null
}

const state: BleServiceState = {
  connectionState: 'disconnected',
  listeners: new Set(),
  useMock: true,
  device: null,
  writeCharacteristic: null,
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
  if (!value) return

  const frame = parseInsoleFrame(value)
  if (frame) notifyListeners(frame)
}

async function connectDevice(device: BluetoothDevice): Promise<void> {
  setConnectionState('connecting')

  device.addEventListener('gattserverdisconnected', () => {
    state.device = null
    state.writeCharacteristic = null
    setConnectionState('disconnected')
  })

  const server = await device.gatt?.connect()
  if (!server) throw new Error('Failed to connect to GATT server')

  const service = await server.getPrimaryService(SERVICE_UUID)
  const notifyChar = await service.getCharacteristic(NOTIFY_CHAR_UUID)

  notifyChar.addEventListener('characteristicvaluechanged', handleCharacteristicValue)
  await notifyChar.startNotifications()

  // Optional write characteristic for control commands
  try {
    const writeChar = await service.getCharacteristic(WRITE_CHAR_UUID)
    state.writeCharacteristic = writeChar
  } catch {
    state.writeCharacteristic = null
  }

  state.device = device
  setConnectionState('connected')
}

/* ── Public API ── */

export function subscribeFrames(listener: FrameListener): () => void {
  state.listeners.add(listener)
  return () => { state.listeners.delete(listener) }
}

export function getConnectionState(): BleConnectionState {
  return state.connectionState
}

export function setUseMock(useMock: boolean): void {
  state.useMock = useMock
}

export async function connect(): Promise<void> {
  if (state.connectionState === 'connected' || state.connectionState === 'connecting') return

  if (state.useMock) {
    setConnectionState('connecting')
    resetMockStream()
    startMockStream(notifyListeners, 20)
    setConnectionState('connected')
    return
  }

  // Try reconnect saved device first
  try {
    await reconnectSavedDevice()
  } catch {
    throw new Error('No device available for connection')
  }
}

export async function disconnect(): Promise<void> {
  if (state.useMock) {
    stopMockStream()
    setConnectionState('disconnected')
    return
  }

  if (state.device?.gatt?.connected) {
    state.device.gatt.disconnect()
  }
  state.device = null
  state.writeCharacteristic = null
  setConnectionState('disconnected')
}

/**
 * Launch system BLE picker and pair a new device.
 */
export async function scanAndConnect(): Promise<SavedDeviceInfo> {
  if (!navigator.bluetooth) {
    throw new Error('Web Bluetooth is not available in this browser.')
  }

  const device = await navigator.bluetooth.requestDevice({
    filters: [{ services: [SERVICE_UUID] }],
    optionalServices: [SERVICE_UUID],
  })

  await connectDevice(device)

  const info: SavedDeviceInfo = {
    deviceId: device.id,
    deviceName: device.name ?? 'Magic Insole',
    pairedAt: Date.now(),
    lastConnectedAt: Date.now(),
  }
  saveDevice(info)
  setUseMock(false)

  return info
}

/**
 * Attempt to reconnect a previously saved device.
 */
export async function reconnectSavedDevice(deviceId?: string): Promise<boolean> {
  if (!navigator.bluetooth) return false

  const devices = getSavedDevices()
  const target = deviceId
    ? findDevice(deviceId)
    : devices.length > 0 ? devices[0] : undefined

  if (!target) return false

  // Web Bluetooth getDevices() returns previously granted devices
  const knownDevices = await navigator.bluetooth.getDevices?.() ?? []
  const device = knownDevices.find((d) => d.id === target.deviceId)

  if (device) {
    await connectDevice(device)
    updateLastConnected(target.deviceId)
    setUseMock(false)
    return true
  }

  // Fall back to system picker
  try {
    await scanAndConnect()
    return true
  } catch {
    return false
  }
}

/**
 * Forget a saved device.
 */
export function forgetDevice(id: string): void {
  removeDevice(id)
}

/**
 * Write a control command to the device (e.g., balance assessment mode).
 */
export async function writeCommand(cmd: number, param: number): Promise<void> {
  if (!state.writeCharacteristic) {
    throw new Error('Write characteristic not available')
  }

  const buffer = new ArrayBuffer(2)
  const view = new DataView(buffer)
  view.setUint8(0, cmd)
  view.setUint8(1, param)

  await state.writeCharacteristic.writeValueWithResponse?.(buffer)
      ?? state.writeCharacteristic.writeValue(buffer)
}

/**
 * Start balance assessment mode. Sends command 0x02 0x01 to the device.
 * In mock mode, pushes the balance mock frame sequence.
 */
export function startBalanceAssessment(onFrame: FrameListener): void {
  if (state.useMock) {
    startBalanceMockStream(onFrame)
    return
  }

  writeCommand(0x02, 0x01).catch(console.error)
}

export { getSavedDevices }
