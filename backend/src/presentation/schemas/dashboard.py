from pydantic import BaseModel


# ── 统计卡片 ──
class DashboardStats(BaseModel):
    active_tasks: int
    today_success: int
    success_rate_7d: float
    alert_count: int
    active_tasks_delta: int
    today_success_delta: int
    success_rate_delta: float


# ── 执行趋势 ──
class TrendData(BaseModel):
    dates: list[str]
    success: list[int]
    failed: list[int]


# ── 平台分布 ──
class PlatformDistribution(BaseModel):
    name: str
    value: int


# ── 最近执行 ──
class RecentRun(BaseModel):
    task_name: str
    task_key: str
    platform: str
    shop: str
    status: str
    duration_ms: int | None
    started_at: str


# ── 账号健康度 ──
class PlatformHealth(BaseModel):
    name: str
    status: str


class AccountHealth(BaseModel):
    total: int
    healthy: int
    warning: int
    invalid: int
    platforms: list[PlatformHealth]


# ── 待处理事项 ──
class TodoItem(BaseModel):
    priority: str
    text: str
    tag: str
    time: str


# ── 通用响应 ──
class ApiResponse[T](BaseModel):
    code: int = 0
    message: str = "ok"
    data: T
