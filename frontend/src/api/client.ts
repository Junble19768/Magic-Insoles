import type {
  ActivityHistory,
  ActivitySummary,
  GaitSummary,
  GpsRoute,
  ReportData,
  ReportHistoryResponse,
  ReportResponse,
} from '@/types'

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

// ── Reports ──

export async function fetchTodayReport(): Promise<ReportData> {
  return request<ReportData>('/report/today')
}

export async function fetchHistory(days = 7): Promise<ReportHistoryResponse> {
  return request<ReportHistoryResponse>(`/report/history?days=${days}`)
}

export async function fetchReport(period: 'today' | 'week' | 'month'): Promise<ReportResponse> {
  return request<ReportResponse>(`/report?period=${period}`)
}

// ── Activity ──

export async function fetchActivityToday(): Promise<ActivitySummary> {
  return request<ActivitySummary>('/activity/today')
}

export async function fetchActivityHistory(days = 7): Promise<ActivityHistory> {
  return request<ActivityHistory>(`/activity/history?days=${days}`)
}

// ── Gait ──

export async function fetchGaitSummary(date: string): Promise<GaitSummary> {
  return request<GaitSummary>(`/gait/summary?date=${date}`)
}

// ── GPS ──

export async function fetchGpsRoutes(date: string): Promise<GpsRoute> {
  return request<GpsRoute>(`/gps/routes?date=${date}`)
}
