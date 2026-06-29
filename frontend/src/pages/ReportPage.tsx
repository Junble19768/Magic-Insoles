import { useCallback, useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { fetchHistory, fetchReport } from '@/api/client'
import { HistoryPicker } from '@/components/HistoryPicker'
import { PeriodSelector } from '@/components/report/PeriodSelector'
import { ReportCard } from '@/components/ReportCard'
import type { ReportData, ReportPeriod } from '@/types'

type PageState =
  | { status: 'loading' }
  | { status: 'empty'; message: string }
  | { status: 'error'; message: string }
  | { status: 'ready'; report: ReportData }

export function ReportPage(): ReactElement {
  const [period, setPeriod] = useState<ReportPeriod>('today')
  const [pageState, setPageState] = useState<PageState>({ status: 'loading' })
  const [historyDates, setHistoryDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')

  const load = useCallback(async (p: ReportPeriod) => {
    setPageState({ status: 'loading' })

    try {
      const [reportRes, history] = await Promise.all([
        fetchReport(p),
        fetchHistory(7),
      ])

      const report: ReportData = {
        date: reportRes.dateRange.end,
        reportText: reportRes.reportText,
        stepCount: reportRes.stepCount,
        gaitSummary: reportRes.gaitSummary,
        generatedAt: reportRes.generatedAt,
      }

      const dates = history.reports.map((item) => item.date)
      setHistoryDates(dates.length > 0 ? dates : [report.date])
      setSelectedDate(report.date)
      setPageState({ status: 'ready', report })
    } catch (error) {
      const message = error instanceof Error ? error.message : '加载报告失败'
      if (message.includes('尚未生成')) {
        setPageState({ status: 'empty', message })
        return
      }
      setPageState({ status: 'error', message })
    }
  }, [])

  useEffect(() => {
    void load(period)
  }, [load, period])

  const handlePeriodChange = useCallback((next: ReportPeriod) => {
    setPeriod(next)
  }, [])

  const handleDateChange = useCallback(async (date: string) => {
    setSelectedDate(date)

    if (pageState.status !== 'ready') return
    if (pageState.report.date === date) return

    try {
      const [, history] = await Promise.all([
        fetchReport('today'),
        fetchHistory(30),
      ])

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
  }, [pageState])

  return (
    <div className="page">
      <header className="page__header">
        <h1>运动报告</h1>
        <p>AI 生成的步态健康分析报告</p>
      </header>

      <PeriodSelector period={period} onChange={handlePeriodChange} />

      {historyDates.length > 0 ? (
        <HistoryPicker
          dates={historyDates}
          selectedDate={selectedDate || historyDates[0]}
          onChange={(date) => { void handleDateChange(date) }}
        />
      ) : null}

      {pageState.status === 'loading' ? (
        <p className="state-placeholder">加载中...</p>
      ) : null}

      {pageState.status === 'empty' ? (
        <p className="state-placeholder">{pageState.message}</p>
      ) : null}

      {pageState.status === 'error' ? (
        <p className="state-placeholder state-placeholder--error">{pageState.message}</p>
      ) : null}

      {pageState.status === 'ready' ? <ReportCard report={pageState.report} /> : null}
    </div>
  )
}
