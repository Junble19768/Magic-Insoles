import type { ReactElement } from 'react'

interface MetricCardProps {
  label: string
  value: string | number
  unit?: string
}

export function MetricCard({ label, value, unit }: MetricCardProps): ReactElement {
  return (
    <div className="metric-card">
      <p className="metric-card__label">{label}</p>
      <p className="metric-card__value">
        {value}
        {unit ? <span className="metric-card__unit">{unit}</span> : null}
      </p>
    </div>
  )
}
