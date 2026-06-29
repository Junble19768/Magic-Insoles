import type { ReactElement } from 'react'
import type { FootAnalysis, GaitClass } from '@/types'

interface GaitClassificationCardProps {
  left: FootAnalysis
  right: FootAnalysis
}

const LABEL: Record<GaitClass, string> = {
  normal: '正常',
  in_toe: '内八',
  out_toe: '外八',
}

export function GaitClassificationCard({ left, right }: GaitClassificationCardProps): ReactElement {
  return (
    <div className="gait-assessment">
      <h3>步态分析结果</h3>
      <p>
        左脚：{LABEL[left.classification]}（置信度 {Math.round(left.confidence * 100)}%）
        {' | '}
        右脚：{LABEL[right.classification]}（置信度 {Math.round(right.confidence * 100)}%）
      </p>
      <p>
        {left.classification === 'normal' && right.classification === 'normal'
          ? '综合评估：步态正常，继续保持良好的运动习惯。'
          : '综合评估：存在步态偏差异常，建议关注足跟受力情况，鼓励每天进行足底肌肉训练。'}
      </p>
    </div>
  )
}
