import { useCallback, useEffect, useRef, useState } from 'react'
import { startBalanceAssessment, subscribeFrames } from '@/ble/bleService'
import { calculateBalanceScore, calculateCop } from '@/viz/cop'
import type { BalanceResult, BalanceStatus, CopPoint, FootCop, PressureFrame } from '@/types'

interface BalanceAssessmentState {
  status: BalanceStatus
  elapsedMs: number
  footCop: FootCop
  postureTip: string
  result: BalanceResult | null
}

const INITIAL: BalanceAssessmentState = {
  status: 'idle',
  elapsedMs: 0,
  footCop: {
    left: { x: 0, y: 0, pressure: 0 },
    right: { x: 0, y: 0, pressure: 0 },
  },
  postureTip: '',
  result: null,
}

function resolvePostureTip(left: CopPoint, right: CopPoint): string {
  const avgX = (left.x + right.x) / 2
  const avgY = (left.y + right.y) / 2

  if (avgX < -0.15) return '重心偏左，请调整'
  if (avgX > 0.15) return '重心偏右，请调整'
  if (avgY < -0.15) return '重心偏前，请调整'
  if (avgY > 0.15) return '重心偏后，请调整'
  return '保持稳定'
}

export function useBalanceAssessment() {
  const [state, setState] = useState<BalanceAssessmentState>(INITIAL)
  const framesRef = useRef<PressureFrame[]>([])
  const unsubscribeRef = useRef<(() => void) | null>(null)

  const start = useCallback(() => {
    framesRef.current = []

    unsubscribeRef.current?.()
    setState({
      status: 'running',
      elapsedMs: 0,
      footCop: INITIAL.footCop,
      postureTip: '准备开始...',
      result: null,
    })

    unsubscribeRef.current = subscribeFrames((frame) => {
      framesRef.current.push(frame)
      const leftCop = calculateCop(frame.leftFoot, 'left')
      const rightCop = calculateCop(frame.rightFoot, 'right')

      setState((prev) => {
        if (prev.status !== 'running') return prev
        const elapsed = Math.min(30000, prev.elapsedMs + 20)

        if (elapsed >= 30000) {
          unsubscribeRef.current?.()
          const result = calculateBalanceScore(framesRef.current)
          return {
            ...prev,
            status: 'done',
            elapsedMs: 30000,
            footCop: { left: leftCop, right: rightCop },
            postureTip: '',
            result,
          }
        }

        return {
          ...prev,
          elapsedMs: elapsed,
          footCop: { left: leftCop, right: rightCop },
          postureTip: resolvePostureTip(leftCop, rightCop),
        }
      })
    })

    startBalanceAssessment(() => {
      // Balance mode started callback (mock mode handles internally)
    })
  }, [])

  const reset = useCallback(() => {
    unsubscribeRef.current?.()
    framesRef.current = []
    setState(INITIAL)
  }, [])

  useEffect(() => {
    return () => {
      unsubscribeRef.current?.()
    }
  }, [])

  return { ...state, start, reset }
}
