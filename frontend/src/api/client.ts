import type { ReportData, ReportHistoryResponse } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'
const API_KEY = import.meta.env.VITE_API_KEY ?? 'dev-magic-insoles-key'

interface ApiErrorBody {
  status?: string
  message?: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
      ...(init?.headers ?? {}),
    },
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try {
      const body = (await response.json()) as ApiErrorBody
      if (body.message) {
        message = body.message
      }
    } catch {
      // Ignore JSON parse errors for non-JSON responses.
    }
    throw new Error(message)
  }

  return (await response.json()) as T
}

export async function fetchTodayReport(): Promise<ReportData> {
  return request<ReportData>('/report/today')
}

export async function fetchHistory(days = 7): Promise<ReportHistoryResponse> {
  return request<ReportHistoryResponse>(`/report/history?days=${days}`)
}
