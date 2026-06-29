import type { ReactElement } from 'react'
import { useBalanceAssessment } from '@/hooks/useBalanceAssessment'
import { BleDevicePanel } from '@/components/ble/BleDevicePanel'
import { BalanceTimer } from '@/components/balance/BalanceTimer'
import { BalanceCopIndicator } from '@/components/balance/BalanceCopIndicator'
import { PostureTip } from '@/components/balance/PostureTip'
import { BalanceResultCard } from '@/components/balance/BalanceResultCard'

export function BalancePage(): ReactElement {
  const { status, elapsedMs, footCop, postureTip, result, start, reset } = useBalanceAssessment()

  return (
    <div className="page balance-page">
      <header className="page__header">
        <h1>平衡能力评估</h1>
        <p>30 秒站定测试，评估维稳能力</p>
      </header>

      <BleDevicePanel />

      {status === 'idle' && (
        <>
          <p className="state-placeholder">
            请站稳后点击下方按钮开始 30 秒评估
          </p>
          <button type="button" className="btn btn--primary" onClick={start}>
            开始评估
          </button>
        </>
      )}

      {status === 'running' && (
        <>
          <BalanceTimer elapsedMs={elapsedMs} />
          <BalanceCopIndicator footCop={footCop} />
          <PostureTip tip={postureTip} />
        </>
      )}

      {status === 'done' && result && (
        <BalanceResultCard result={result} onRetry={reset} />
      )}
    </div>
  )
}
