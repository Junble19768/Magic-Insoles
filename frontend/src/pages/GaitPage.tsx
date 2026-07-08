import { useCallback, useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { fetchGaitSummary } from '@/api/client'
import { DatePicker } from '@/components/common/DatePicker'
import { GaitClassificationCard } from '@/components/gait/GaitClassificationCard'
import { FootAnalysisCanvas } from '@/viz/FootAnalysisCanvas'
import type { GaitSummary } from '@/types'

type PageState =
  | { status: 'loading' }
  | { status: 'ready'; data: GaitSummary }
  | { status: 'error'; message: string }

export function GaitPage(): ReactElement {
  const today = new Date().toISOString().slice(0, 10)
  const [pageState, setPageState] = useState<PageState>({ status: 'loading' })
  const [selectedDate, setSelectedDate] = useState(today)

  const load = useCallback(async (date: string) => {
    setPageState({ status: 'loading' })
    try {
      const data = await fetchGaitSummary(date)
      setPageState({ status: 'ready', data })
    } catch (error) {
      setPageState({
        status: 'error',
        message: error instanceof Error ? error.message : '加载步态数据失败',
      })
    }
  }, [])

  useEffect(() => {
    void load(selectedDate)
  }, [load, selectedDate])

  const handleDateChange = useCallback((date: string) => {
    setSelectedDate(date)
  }, [])

  return (
    <div className="page">
      <header className="page__header">
        <h1>步态分析</h1>
        <p>历史步态数据回放与内外八分析</p>
      </header>

      <DatePicker value={selectedDate} onChange={handleDateChange} />

      {pageState.status === 'loading' ? (
        <p className="state-placeholder">加载中...</p>
      ) : pageState.status === 'error' ? (
        <p className="state-placeholder state-placeholder--error">{pageState.message}</p>
      ) : (
        <>
          <div className="gait-grid">
            <div className="gait-foot">
              <p className="gait-foot__label">左脚 · 日均压力 + 全天重心轨迹</p>
              <FootAnalysisCanvas
                pressures={pageState.data.leftFoot.pressures}
                copPoints={pageState.data.leftFoot.copPoints}
                side="left"
                showTrajectoryDensity
                showTrajectoryFit
              />
            </div>
            <div className="gait-foot">
              <p className="gait-foot__label">右脚 · 日均压力 + 全天重心轨迹</p>
              <FootAnalysisCanvas
                pressures={pageState.data.rightFoot.pressures}
                copPoints={pageState.data.rightFoot.copPoints}
                side="right"
                showTrajectoryDensity
                showTrajectoryFit
              />
            </div>
          </div>
          <GaitClassificationCard
            left={pageState.data.leftFoot}
            right={pageState.data.rightFoot}
          />
        </>
      )}
    </div>
  )
}
