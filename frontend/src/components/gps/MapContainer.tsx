import { useEffect, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { GpsPoint } from '@/types'

interface MapContainerProps {
  points: readonly GpsPoint[]
  className?: string
}

interface LeafletModule {
  map: (el: HTMLElement) => LMap
  tileLayer: (url: string, opts?: Record<string, unknown>) => LTileLayer
  polyline: (coords: [number, number][], opts?: Record<string, unknown>) => LPolyline
  marker: (coords: [number, number], opts?: Record<string, unknown>) => LMarker
  icon: (opts: Record<string, unknown>) => LIcon
}

interface LMap {
  setView: (center: [number, number], zoom: number) => LMap
  remove: () => void
}

interface LTileLayer {
  addTo: (map: LMap) => void
}

interface LPolyline {
  addTo: (map: LMap) => void
}

interface LMarker {
  addTo: (map: LMap) => void
}

interface LIcon {
  // marker icon
}

export function MapContainer({ points, className }: MapContainerProps): ReactElement {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [error, setError] = useState<string | null>(null)
  const mapRef = useRef<LMap | null>(null)

  useEffect(() => {
    if (points.length === 0) return

    const container = containerRef.current
    if (!container) return

    let cancelled = false

    async function init(): Promise<void> {
      try {
        const L = await loadLeaflet()
        if (cancelled) return

        // Clean up old map
        mapRef.current?.remove()

        const map = L.map(container!)
        mapRef.current = map

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; OpenStreetMap',
        }).addTo(map)

        const coords: [number, number][] = points.map((p) => [p.lat, p.lng])
        L.polyline(coords, { color: '#163B31', weight: 4 }).addTo(map)

        // Start marker (green)
        if (coords.length > 0) {
          L.marker(coords[0], {
            icon: L.icon({
              iconUrl: 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><circle cx="12" cy="12" r="8" fill="#2F8F78" stroke="#fff" stroke-width="2"/></svg>'),
              iconSize: [24, 24],
              iconAnchor: [12, 12],
            }),
          } as Record<string, unknown>).addTo(map)
        }

        // End marker (red)
        if (coords.length > 1) {
          L.marker(coords[coords.length - 1], {
            icon: L.icon({
              iconUrl: 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><circle cx="12" cy="12" r="8" fill="#b42318" stroke="#fff" stroke-width="2"/></svg>'),
              iconSize: [24, 24],
              iconAnchor: [12, 12],
            }),
          } as Record<string, unknown>).addTo(map)
        }

        // Fit bounds
        const bounds = coords.reduce(
          (acc, c) => ({
            minLat: Math.min(acc.minLat, c[0]),
            maxLat: Math.max(acc.maxLat, c[0]),
            minLng: Math.min(acc.minLng, c[1]),
            maxLng: Math.max(acc.maxLng, c[1]),
          }),
          { minLat: 90, maxLat: -90, minLng: 180, maxLng: -180 },
        )
        const centerLat = (bounds.minLat + bounds.maxLat) / 2
        const centerLng = (bounds.minLng + bounds.maxLng) / 2
        const latDiff = bounds.maxLat - bounds.minLat || 0.02
        const lngDiff = bounds.maxLng - bounds.minLng || 0.02
        const zoomLat = Math.floor(Math.log2(360 / latDiff)) - 1
        const zoomLng = Math.floor(Math.log2(360 / lngDiff)) - 1
        const zoom = Math.min(18, Math.max(12, Math.min(zoomLat, zoomLng)))
        map.setView([centerLat, centerLng], zoom)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : '地图加载失败')
      }
    }

    void init()

    return () => {
      cancelled = true
      mapRef.current?.remove()
    }
  }, [points])

  if (error) {
    return <p className="state-placeholder state-placeholder--error">{error}</p>
  }

  if (points.length === 0) {
    return <p className="state-placeholder">当日无 GPS 记录</p>
  }

  return <div className={className ?? 'gps-map'} ref={containerRef} />
}

let leafletPromise: Promise<LeafletModule> | null = null

async function loadLeaflet(): Promise<LeafletModule> {
  if (leafletPromise) return leafletPromise

  leafletPromise = new Promise<LeafletModule>((resolve, reject) => {
    if ((window as unknown as Record<string, unknown>).L) {
      resolve((window as unknown as Record<string, unknown>).L as LeafletModule)
      return
    }

    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(link)

    const script = document.createElement('script')
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.onload = () => resolve((window as unknown as Record<string, unknown>).L as LeafletModule)
    script.onerror = () => reject(new Error('Leaflet JS 加载失败'))
    document.head.appendChild(script)
  })

  return leafletPromise
}
