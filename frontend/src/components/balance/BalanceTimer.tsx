import type { ReactElement } from 'react'

interface BalanceTimerProps {
  elapsedMs: number
  totalMs?: number
}

export function BalanceTimer({ elapsedMs, totalMs = 30000 }: BalanceTimerProps): ReactElement {
  const progress = (elapsedMs / totalMs)
  const radius = 50
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - progress)
  const remaining = Math.max(0, Math.ceil((totalMs - elapsedMs) / 1000))

  return (
    <div className="balance-timer">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={radius} className="balance-timer__track" />
        <circle
          cx="60"
          cy="60"
          r={radius}
          className="balance-timer__progress"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div style={{ position: 'absolute', transform: 'rotate(90deg)', fontSize: '1.4rem', fontWeight: 700, color: 'var(--color-primary)', marginTop: '48px' }}>
        {remaining}s
      </div>
    </div>
  )
}
