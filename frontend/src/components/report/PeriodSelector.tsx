import type { ReactElement } from 'react'
import type { ReportPeriod } from '@/types'

interface PeriodSelectorProps {
  period: ReportPeriod
  onChange: (period: ReportPeriod) => void
}

const PERIODS: readonly { value: ReportPeriod; label: string }[] = [
  { value: 'today', label: '今日' },
  { value: 'week', label: '近一周' },
  { value: 'month', label: '近一月' },
]

export function PeriodSelector({ period, onChange }: PeriodSelectorProps): ReactElement {
  return (
    <div className="period-selector">
      {PERIODS.map((p) => (
        <button
          key={p.value}
          type="button"
          className={`period-selector__tab${period === p.value ? ' period-selector__tab--active' : ''}`}
          onClick={() => onChange(p.value)}
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}
