from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.services.dashboard_service import DashboardService
from config.database import get_db
from presentation.schemas.dashboard import (
    AccountHealth,
    ApiResponse,
    DashboardStats,
    PlatformDistribution,
    RecentRun,
    TodoItem,
    TrendData,
)

router = APIRouter()


def _service(session: AsyncSession = Depends(get_db)) -> DashboardService:
    return DashboardService(session)


@router.get("/stats", response_model=ApiResponse[DashboardStats])
async def get_stats(svc: DashboardService = Depends(_service)):
    data = await svc.get_stats()
    return ApiResponse(data=data)


@router.get("/trend", response_model=ApiResponse[TrendData])
async def get_trend(days: int = 7, svc: DashboardService = Depends(_service)):
    data = await svc.get_trend(days=days)
    return ApiResponse(data=data)


@router.get("/platform", response_model=ApiResponse[list[PlatformDistribution]])
async def get_platform_distribution(svc: DashboardService = Depends(_service)):
    data = await svc.get_platform_distribution()
    return ApiResponse(data=data)


@router.get("/recent-runs", response_model=ApiResponse[list[RecentRun]])
async def get_recent_runs(limit: int = 10, svc: DashboardService = Depends(_service)):
    data = await svc.get_recent_runs(limit=limit)
    return ApiResponse(data=data)


@router.get("/health", response_model=ApiResponse[AccountHealth])
async def get_account_health(svc: DashboardService = Depends(_service)):
    data = await svc.get_account_health()
    return ApiResponse(data=data)


@router.get("/todos", response_model=ApiResponse[list[TodoItem]])
async def get_todos(svc: DashboardService = Depends(_service)):
    data = await svc.get_todos()
    return ApiResponse(data=data)

