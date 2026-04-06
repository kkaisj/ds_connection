import axios from 'axios'

const http = axios.create({ baseURL: '/api/v1' })

export interface DashboardStats {
  active_tasks: number
  today_success: number
  success_rate_7d: number
  alert_count: number
  active_tasks_delta: number
  today_success_delta: number
  success_rate_delta: number
}

export interface TrendData {
  dates: string[]
  success: number[]
  failed: number[]
}

export interface PlatformItem {
  name: string
  value: number
}

export interface RecentRun {
  task_name: string
  task_key: string
  platform: string
  shop: string
  status: 'success' | 'failed' | 'running' | 'pending'
  duration_ms: number | null
  started_at: string
}

export interface HealthData {
  total: number
  healthy: number
  warning: number
  invalid: number
  platforms: { name: string; status: string }[]
}

export interface TodoItem {
  priority: 'high' | 'medium' | 'low'
  text: string
  tag: string
  time: string
}

interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export const dashboardApi = {
  getStats: () => http.get<ApiResponse<DashboardStats>>('/dashboard/stats').then(r => r.data.data),
  getTrend: () => http.get<ApiResponse<TrendData>>('/dashboard/trend').then(r => r.data.data),
  getPlatform: () => http.get<ApiResponse<PlatformItem[]>>('/dashboard/platform').then(r => r.data.data),
  getRecentRuns: () => http.get<ApiResponse<RecentRun[]>>('/dashboard/recent-runs').then(r => r.data.data),
  getHealth: () => http.get<ApiResponse<HealthData>>('/dashboard/health').then(r => r.data.data),
  getTodos: () => http.get<ApiResponse<TodoItem[]>>('/dashboard/todos').then(r => r.data.data),
}
