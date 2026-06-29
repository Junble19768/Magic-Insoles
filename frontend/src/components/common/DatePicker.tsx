import type { ReactElement } from 'react'

interface DatePickerProps {
  value: string
  onChange: (date: string) => void
}

export function DatePicker({ value, onChange }: DatePickerProps): ReactElement {
  const today = new Date().toISOString().slice(0, 10)

  return (
    <div className="date-picker">
      <label htmlFor="gait-date">选择日期</label>
      <input
        id="gait-date"
        type="date"
        max={today}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}
