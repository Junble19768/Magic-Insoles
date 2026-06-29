import type { SavedDeviceInfo } from '@/types'

const STORAGE_KEY = 'magic-insoles-devices'

function readAll(): SavedDeviceInfo[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    return JSON.parse(raw) as SavedDeviceInfo[]
  } catch {
    return []
  }
}

function writeAll(devices: SavedDeviceInfo[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(devices))
}

export function getSavedDevices(): readonly SavedDeviceInfo[] {
  return readAll()
}

export function saveDevice(info: SavedDeviceInfo): void {
  const devices = readAll().filter((d) => d.deviceId !== info.deviceId)
  devices.push(info)
  writeAll(devices)
}

export function removeDevice(id: string): void {
  writeAll(readAll().filter((d) => d.deviceId !== id))
}

export function forgetDevice(id: string): void {
  removeDevice(id)
}

export function updateLastConnected(id: string): void {
  const devices = readAll()
  const target = devices.find((d) => d.deviceId === id)
  if (target) {
    target.lastConnectedAt = Date.now()
    writeAll(devices)
  }
}

export function findDevice(id: string): SavedDeviceInfo | undefined {
  return readAll().find((d) => d.deviceId === id)
}
