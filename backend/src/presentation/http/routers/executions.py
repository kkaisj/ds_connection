"""
执行记录路由层
提供任务运行记录的查询接口，支持按任务/状态/时间筛选。
支持查看单次运行的步骤级日志。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from infrastructure.persistence.models.models import (
    ConnectorApp,
    Platform,
    ShopAccount,
    TaskInstance,
    TaskRun,
    TaskRunLog,
)

router = APIRouter()


@router.get("")
async def list_runs(
    task_id: int | None = Query(None, description="按任务 ID 筛选"),
    status: str | None = Query(None, description="按状态筛选 pending/running/success/failed/cancelled"),
    limit: int = Query(20, le=100, description="每页条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    session: AsyncSession = Depends(get_db),
):
    """
    查询任务执行记录列表。
    关联查询任务名、应用名、平台、店铺信息。
    支持分页和按任务/状态筛选。
    """
    stmt = (
        select(TaskRun, TaskInstance, ConnectorApp, Platform, ShopAccount)
        .join(TaskInstance, TaskRun.task_id == TaskInstance.id)
        .join(ConnectorApp, TaskInstance.app_id == ConnectorApp.id)
        .join(Platform, ConnectorApp.platform_id == Platform.id)
        .join(ShopAccount, TaskInstance.account_id == ShopAccount.id)
    )

    if task_id is not None:
        stmt = stmt.where(TaskRun.task_id == task_id)
    if status:
        stmt = stmt.where(TaskRun.status == status)

    stmt = stmt.order_by(TaskRun.started_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)

    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": run.id,
                "task_id": run.task_id,
                "task_name": task.name,
                "app_name": app.name,
                "platform_name": plat.name,
                "shop_name": account.shop_name,
                "trigger_type": run.trigger_type,
                "status": run.status,
                "retry_count": run.retry_count,
                "duration_ms": run.duration_ms,
                "error_code": run.error_code,
                "error_message": run.error_message,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "ended_at": run.ended_at.isoformat() if run.ended_at else None,
            }
            for run, task, app, plat, account in result.all()
        ],
    }


@router.get("/{run_id}/logs")
async def get_run_logs(run_id: int, session: AsyncSession = Depends(get_db)):
    """
    查询单次运行的步骤级日志。
    按时间正序排列，展示每个步骤的级别、消息和扩展数据。
    """
    stmt = (
        select(TaskRunLog)
        .where(TaskRunLog.run_id == run_id)
        .order_by(TaskRunLog.created_at)
    )
    result = await session.execute(stmt)

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "run_id": run_id,
            "items": [
                {
                    "step": log.step,
                    "level": log.level,
                    "message": log.message,
                    "ext": log.ext,
                    "ts": log.created_at.isoformat() if log.created_at else None,
                }
                for log in result.scalars().all()
            ],
        },
    }

