import { useCallback, useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { fetchGpsRoutes } from '@/api/client'
import { MapContainer } from '@/components/gps/MapContainer'
import { DatePicker } from '@/components/common/DatePicker'
import type { GpsRoute } from '@/types'

type PageState =
  | { status: 'loading' }
  | { status: 'ready'; data: GpsRoute }
  | { status: 'empty' }
  | { status: 'error'; message: string }

export function GpsPage(): ReactElement {
  const today = new Date().toISOString().slice(0, 10)
  const [pageState, setPageState] = useState<PageState>({ status: 'loading' })
  const [selectedDate, setSelectedDate] = useState(today)

  const load = useCallback(async (date: string) => {
    setPageState({ status: 'loading' })
    try {
      const data = await fetchGpsRoutes(date)
      if (data.points.length === 0) {
        setPageState({ status: 'empty' })
      } else {
        setPageState({ status: 'ready', data })
      }
    } catch (error) {
      setPageState({
        status: 'error',
        message: error instanceof Error ? error.message : '加载轨迹数据失败',
      })
    }
  }, [])

  useEffect(() => {
    void load(selectedDate)
  }, [load, selectedDate])

  return (
    <div className="page">
      <header className="page__header">
        <h1>GPS 轨迹</h1>
        <p>户外活动路径记录</p>
      </header>

      <DatePicker value={selectedDate} onChange={setSelectedDate} />

      {pageState.status === 'loading' ? (
        <p className="state-placeholder">加载中...</p>
      ) : pageState.status === 'error' ? (
        <p className="state-placeholder state-placeholder--error">{pageState.message}</p>
      ) : pageState.status === 'empty' ? (
        <p className="state-placeholder">当日无 GPS 记录</p>
      ) : (
        <>
          <MapContainer points={pageState.data.points} />
          <div className="gps-info">
            <div className="gps-info__item">
              <span className="gps-info__label">总距离</span>
              <span className="gps-info__value">{pageState.data.totalDistanceKm} km</span>
            </div>
            <div className="gps-info__item">
              <span className="gps-info__label">时长</span>
              <span className="gps-info__value">{pageState.data.durationMinutes} 分钟</span>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
