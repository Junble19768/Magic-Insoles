import { useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { fetchActivityHistory, fetchActivityToday } from '@/api/client'
import { StepsBarChart } from '@/components/activity/StepsBarChart'
import type { ActivityHistoryDay, ActivitySummary } from '@/types'

type PageState =
  | { status: 'loading' }
  | { status: 'ready'; summary: ActivitySummary; history: readonly ActivityHistoryDay[] }
  | { status: 'error'; message: string }

export function ActivityPage(): ReactElement {
  const [pageState, setPageState] = useState<PageState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    async function load(): Promise<void> {
      try {
        const [summary, history] = await Promise.all([
          fetchActivityToday(),
          fetchActivityHistory(7),
        ])
        if (cancelled) return
        setPageState({ status: 'ready', summary, history: history.days })
      } catch (error) {
        if (cancelled) return
        setPageState({
          status: 'error',
          message: error instanceof Error ? error.message : '加载运动数据失败',
        })
      }
    }

    void load()

    return () => { cancelled = true }
  }, [])

  if (pageState.status === 'loading') {
    return (
      <div className="page">
        <header className="page__header">
          <h1>运动情况</h1>
          <p>今日步数、运动时长、距离与近期趋势</p>
        </header>
        <div className="activity-stats">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="metric-card skeleton" style={{ height: '6rem' }} />
          ))}
        </div>
      </div>
    )
  }

  if (pageState.status === 'error') {
    return (
      <div className="page">
        <header className="page__header">
          <h1>运动情况</h1>
        </header>
        <p className="state-placeholder state-placeholder--error">{pageState.message}</p>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="page__header">
        <h1>运动情况</h1>
        <p>今日运动概况与近 7 天步数趋势</p>
      </header>

      <div className="activity-stats">
        <div className="metric-card">
          <p className="metric-card__label">今日步数</p>
          <p className="metric-card__value">
            {pageState.summary.steps.toLocaleString()}
            <span className="metric-card__unit">步</span>
          </p>
        </div>
        <div className="metric-card">
          <p className="metric-card__label">有效运动时长</p>
          <p className="metric-card__value">
            {pageState.summary.activeMinutes}
            <span className="metric-card__unit">分钟</span>
          </p>
        </div>
        <div className="metric-card">
          <p className="metric-card__label">运动距离</p>
          <p className="metric-card__value">
            {pageState.summary.distanceKm}
            <span className="metric-card__unit">km</span>
          </p>
        </div>
      </div>

      <div className="dashboard__chart">
        <h3 className="dashboard__section-title">最近 7 天步数</h3>
        <StepsBarChart days={pageState.history} />
      </div>
    </div>
  )
}
