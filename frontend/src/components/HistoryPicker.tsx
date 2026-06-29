interface HistoryPickerProps {
  dates: readonly string[]
  selectedDate: string
  onChange: (date: string) => void
}

export function HistoryPicker({ dates, selectedDate, onChange }: HistoryPickerProps) {
  return (
    <label className="history-picker">
      <span>选择日期</span>
      <select value={selectedDate} onChange={(event) => onChange(event.target.value)}>
        {dates.map((date) => (
          <option key={date} value={date}>
            {date}
          </option>
        ))}
      </select>
    </label>
  )
}
