import type { GaitClass, PressureFrame } from '@/types'

interface GaitStatusBarProps {
  frame: PressureFrame | null
  abnormalStreak: number
}

const GAIT_LABEL: Record<GaitClass, string> = {
  normal: '正常',
  in_toe: '内八',
  out_toe: '外八',
}

const GAIT_STATE_LABEL = {
  standing: '站立',
  walking: '行走',
  running: '跑步',
} as const

export function GaitStatusBar({ frame, abnormalStreak }: GaitStatusBarProps) {
  const gaitClass = frame?.mlClass ?? 'normal'
  const confidence = frame?.mlConf ?? 0
  const gaitState = frame?.gaitState ?? 'standing'
  const showToast = abnormalStreak >= 5

  return (
    <section className="gait-status">
      <div className="gait-status__row">
        <div>
          <p className="gait-status__label">步态分类</p>
          <p className={`gait-status__value gait-status__value--${gaitClass}`}>
            {GAIT_LABEL[gaitClass]}
          </p>
        </div>
        <div>
          <p className="gait-status__label">运动状态</p>
          <p className="gait-status__value">{GAIT_STATE_LABEL[gaitState]}</p>
        </div>
        <div>
          <p className="gait-status__label">置信度</p>
          <p className="gait-status__value">{Math.round(confidence * 100)}%</p>
        </div>
      </div>

      <div className="gait-status__meter" aria-hidden="true">
        <div className="gait-status__meter-fill" style={{ width: `${confidence * 100}%` }} />
      </div>

      {frame ? (
        <p className="gait-status__meta">
          步数 {frame.stepCount} · 电量 {frame.battery}%
        </p>
      ) : (
        <p className="gait-status__meta">等待数据…</p>
      )}

      {showToast ? (
        <div className="gait-status__toast" role="status">
          检测到连续异常步态，请注意调整姿势
        </div>
      ) : null}
    </section>
  )
}
