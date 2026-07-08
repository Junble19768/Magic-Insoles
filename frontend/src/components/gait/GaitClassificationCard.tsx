import type { ReactElement } from 'react'
import type { FootAnalysis, GaitClass } from '@/types'
import { copPointsToPlotArrays, fitCopTrajectoryLine } from '@/viz/cop'
import { getBoundaryAssets } from '@/viz/boundary/assets'
import { normalizeCopPointsForDisplay } from '@/viz/boundary/transform'

interface GaitClassificationCardProps {
  left: FootAnalysis
  right: FootAnalysis
}

const LABEL: Record<GaitClass, string> = {
  normal: '正常',
  in_toe: '内八',
  out_toe: '外八',
}

const FALLBACK_BOUNDARY_WIDTH = 132
const FALLBACK_BOUNDARY_HEIGHT = 324

function formatTrajectoryAngle(copPoints: FootAnalysis['copPoints']): string {
  const assets = getBoundaryAssets()
  const displayWidth = assets?.canvas.width ?? FALLBACK_BOUNDARY_WIDTH
  const displayHeight = assets?.canvas.height ?? FALLBACK_BOUNDARY_HEIGHT
  const displayCopPoints = normalizeCopPointsForDisplay(copPoints, displayWidth, displayHeight)
  const { xs, ys } = copPointsToPlotArrays(displayCopPoints)
  const fit = fitCopTrajectoryLine(xs, ys)
  if (!fit) {
    return '—'
  }
  return `${fit.angleDeg.toFixed(1)}°`
}

export function GaitClassificationCard({ left, right }: GaitClassificationCardProps): ReactElement {
  const leftAngle = formatTrajectoryAngle(left.copPoints)
  const rightAngle = formatTrajectoryAngle(right.copPoints)

  return (
    <div className="gait-assessment">
      <h3>步态分析结果</h3>
      <p>
        左脚：{LABEL[left.classification]}（置信度 {Math.round(left.confidence * 100)}%）
        {' | '}
        右脚：{LABEL[right.classification]}（置信度 {Math.round(right.confidence * 100)}%）
      </p>
      <p>
        重心轨迹夹角（相对趾→跟方向）：左脚 θ={leftAngle}，右脚 θ={rightAngle}
      </p>
      <p>
        {left.classification === 'normal' && right.classification === 'normal'
          ? '综合评估：步态正常，继续保持良好的运动习惯。'
          : '综合评估：存在步态偏差异常，建议关注足跟受力情况，鼓励每天进行足底肌肉训练。'}
      </p>
    </div>
  )
}
