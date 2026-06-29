import type { ReactElement } from 'react'

interface PostureTipProps {
  tip: string
}

export function PostureTip({ tip }: PostureTipProps): ReactElement {
  if (!tip) return <div />

  const isOk = tip.includes('稳定')

  return (
    <p className={`balance-posture-tip ${isOk ? 'balance-posture-tip--ok' : 'balance-posture-tip--warn'}`}>
      {isOk ? `${tip} ✓` : tip}
    </p>
  )
}
