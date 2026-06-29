import type { ReportData } from '@/types'

interface ReportCardProps {
  report: ReportData
}

export function ReportCard({ report }: ReportCardProps) {
  return (
    <article className="report-card">
      <header className="report-card__header">
        <h2>{report.date}</h2>
        <p>{report.gaitSummary}</p>
      </header>
      <p className="report-card__steps">今日步数：{report.stepCount}</p>
      <div className="report-card__body">{report.reportText}</div>
    </article>
  )
}
