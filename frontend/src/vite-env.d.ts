/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_API_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface BluetoothRemoteGATTCharacteristic extends EventTarget {
  readonly value: DataView | null
  startNotifications(): Promise<BluetoothRemoteGATTCharacteristic>
  writeValue(value: ArrayBuffer): Promise<void>
  writeValueWithResponse(value: ArrayBuffer): Promise<void>
  addEventListener(
    type: 'characteristicvaluechanged',
    listener: (event: Event) => void,
  ): void
  removeEventListener(
    type: 'characteristicvaluechanged',
    listener: (event: Event) => void,
  ): void
}

interface BluetoothRemoteGATTService {
  getCharacteristic(characteristic: string): Promise<BluetoothRemoteGATTCharacteristic>
}

interface BluetoothRemoteGATTServer {
  readonly connected: boolean
  connect(): Promise<BluetoothRemoteGATTServer>
  disconnect(): void
  getPrimaryService(service: string): Promise<BluetoothRemoteGATTService>
}

interface BluetoothDevice extends EventTarget {
  readonly id: string
  readonly name: string | undefined
  readonly gatt: BluetoothRemoteGATTServer | undefined
}

interface Bluetooth {
  requestDevice(options: {
    filters: Array<{ services: string[] }>
    optionalServices?: string[]
  }): Promise<BluetoothDevice>
  getDevices(): Promise<BluetoothDevice[]>
}

interface Navigator {
  bluetooth?: Bluetooth
}
