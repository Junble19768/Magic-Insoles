import { useEffect, useMemo, useState } from 'react'
import { fetchHistory, fetchTodayReport } from '@/api/client'
import { HistoryPicker } from '@/components/HistoryPicker'
import { ReportCard } from '@/components/ReportCard'
import type { ReportData } from '@/types'

type ReportPageState =
  | { status: 'loading' }
  | { status: 'empty'; message: string }
  | { status: 'error'; message: string }
  | { status: 'ready'; report: ReportData }

export function ReportPage() {
  const [pageState, setPageState] = useState<ReportPageState>({ status: 'loading' })
  const [historyDates, setHistoryDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadReports(): Promise<void> {
      setPageState({ status: 'loading' })

      try {
        const [today, history] = await Promise.all([
          fetchTodayReport(),
          fetchHistory(7),
        ])

        if (cancelled) {
          return
        }

        const dates = history.reports.map((item) => item.date)
        setHistoryDates(dates.length > 0 ? dates : [today.date])
        setSelectedDate(today.date)
        setPageState({ status: 'ready', report: today })
      } catch (error) {
        if (cancelled) {
          return
        }

        const message = error instanceof Error ? error.message : '加载报告失败'
        if (message.includes('尚未生成')) {
          setPageState({ status: 'empty', message })
          return
        }

        setPageState({ status: 'error', message })
      }
    }

    void loadReports()

    return () => {
      cancelled = true
    }
  }, [])

  const selectedReport = useMemo(() => {
    if (pageState.status !== 'ready') {
      return null
    }
    return pageState.report
  }, [pageState])

  const handleDateChange = async (date: string): Promise<void> => {
    setSelectedDate(date)

    if (selectedReport?.date === date) {
      return
    }

    try {
      const history = await fetchHistory(30)
      const match = history.reports.find((item) => item.date === date)
      if (!match) {
        setPageState({ status: 'empty', message: '该日期暂无报告' })
        return
      }

      setPageState({
        status: 'ready',
        report: {
          date: match.date,
          reportText: match.reportText,
          stepCount: match.stepCount,
          gaitSummary: match.gaitSummary,
          generatedAt: Date.now(),
        },
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : '切换日期失败'
      setPageState({ status: 'error', message })
    }
  }

  return (
    <div className="page report-page">
      <header className="page__header">
        <h1>健康日报</h1>
        <p>远程查看 AI 生成的步态报告</p>
      </header>

      {historyDates.length > 0 ? (
        <HistoryPicker
          dates={historyDates}
          selectedDate={selectedDate || historyDates[0]}
          onChange={(date) => {
            void handleDateChange(date)
          }}
        />
      ) : null}

      {pageState.status === 'loading' ? (
        <p className="report-page__state">加载中…</p>
      ) : null}

      {pageState.status === 'empty' ? (
        <p className="report-page__state">{pageState.message}</p>
      ) : null}

      {pageState.status === 'error' ? (
        <p className="report-page__state report-page__state--error">{pageState.message}</p>
      ) : null}

      {pageState.status === 'ready' ? <ReportCard report={pageState.report} /> : null}
    </div>
  )
}
