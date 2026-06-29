import type { ReactElement } from 'react'
import type { BalanceResult } from '@/types'
import { FootAnalysisCanvas } from '@/viz/FootAnalysisCanvas'

interface BalanceResultCardProps {
  result: BalanceResult
  onRetry: () => void
}

const GRADE_LABEL: Record<string, string> = {
  excellent: '优秀',
  good: '良好',
  fair: '一般',
  needs_improvement: '需改善',
}

export function BalanceResultCard({ result, onRetry }: BalanceResultCardProps): ReactElement {
  return (
    <div className="balance-result">
      <p className="balance-result__score">{result.score}</p>
      <p className="balance-result__grade">{GRADE_LABEL[result.grade] ?? result.grade}</p>

      <div className="gait-grid">
        <div className="gait-foot">
          <p className="gait-foot__label">左脚平均压力</p>
          <FootAnalysisCanvas
            pressures={result.leftAvgPressures}
            copPoints={result.leftCopTrajectory.slice(0, 100)}
            side="left"
          />
        </div>
        <div className="gait-foot">
          <p className="gait-foot__label">右脚平均压力</p>
          <FootAnalysisCanvas
            pressures={result.rightAvgPressures}
            copPoints={result.rightCopTrajectory.slice(0, 100)}
            side="right"
          />
        </div>
      </div>

      <button type="button" className="btn btn--primary" onClick={onRetry}>
        重新评估
      </button>
    </div>
  )
}
