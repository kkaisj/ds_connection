"""
连接任务路由层
提供任务实例的增删改查、手动执行和重试接口。
所有查询过滤 is_deleted=False，删除操作为软删除。
"""

import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from infrastructure.persistence.models.models import (
    ConnectorApp,
    NotificationConfig,
    Platform,
    ShopAccount,
    StorageConfig,
    TaskInstance,
    TaskRun,
)

router = APIRouter()


class CreateTaskBody(BaseModel):
    """创建任务的请求参数"""
    app_id: int
    account_id: int
    storage_config_id: int
    notification_config_id: int
    name: str
    cron_expr: str = "0 8 * * *"
    params: dict | None = None


class UpdateTaskBody(BaseModel):
    """更新任务的请求参数，所有字段可选"""
    name: str | None = None
    cron_expr: str | None = None
    status: str | None = None
    storage_config_id: int | None = None
    notification_config_id: int | None = None
    params: dict | None = None


@router.get("")
async def list_tasks(
    platform: str | None = Query(None, description="按平台 code 筛选"),
    status: str | None = Query(None, description="按状态筛选 enabled/paused"),
    keyword: str | None = Query(None, description="按任务名/应用名/店铺名搜索"),
    session: AsyncSession = Depends(get_db),
):
    """查询未删除的任务实例列表，支持平台/状态/关键词筛选。"""
    # 子查询：按任务维度取“最新一条执行记录状态”。
    latest_run_status_subq = (
        select(TaskRun.status)
        .where(TaskRun.task_id == TaskInstance.id)
        .order_by(TaskRun.started_at.desc(), TaskRun.id.desc())
        .limit(1)
        .scalar_subquery()
    )

    stmt = (
        select(
            TaskInstance,
            ConnectorApp,
            Platform,
            ShopAccount,
            latest_run_status_subq.label("last_run_status"),
        )
        .join(ConnectorApp, TaskInstance.app_id == ConnectorApp.id)
        .join(Platform, ConnectorApp.platform_id == Platform.id)
        .join(ShopAccount, TaskInstance.account_id == ShopAccount.id)
        .where(TaskInstance.is_deleted.is_(False))
    )

    if platform:
        stmt = stmt.where(Platform.code == platform)
    if status:
        stmt = stmt.where(TaskInstance.status == status)
    if keyword:
        # 模糊搜索任务名、应用名、店铺名
        like = f"%{keyword}%"
        from sqlalchemy import or_

        stmt = stmt.where(
            or_(
                TaskInstance.name.like(like),
                ConnectorApp.name.like(like),
                ShopAccount.shop_name.like(like),
            )
        )

    stmt = stmt.order_by(TaskInstance.id.desc())
    result = await session.execute(stmt)

    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": task.id,
                "name": task.name,
                "app_id": task.app_id,
                "account_id": task.account_id,
                "storage_config_id": task.storage_config_id,
                "notification_config_id": task.notification_config_id,
                "cron_expr": task.cron_expr,
                "status": task.status,
                "params": task.params,
                "app_name": app.name,
                "platform_code": plat.code,
                "platform_name": plat.name,
                "shop_name": account.shop_name,
                "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
                "last_run_status": last_run_status,
                "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
            for task, app, plat, account, last_run_status in result.all()
        ],
    }


@router.post("")
async def create_task(body: CreateTaskBody, session: AsyncSession = Depends(get_db)):
    """创建新的任务实例。"""
    task = TaskInstance(
        app_id=body.app_id,
        account_id=body.account_id,
        storage_config_id=body.storage_config_id,
        notification_config_id=body.notification_config_id,
        name=body.name,
        cron_expr=body.cron_expr,
        params=body.params,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return {"code": 0, "message": "ok", "data": {"id": task.id, "name": task.name}}


@router.patch("/{task_id}")
async def update_task(task_id: int, body: UpdateTaskBody, session: AsyncSession = Depends(get_db)):
    """更新任务实例，支持修改名称、调度、状态和参数。"""
    task = await session.get(TaskInstance, task_id)
    if not task or task.is_deleted:
        return {"code": 404, "message": "任务不存在", "data": None}

    if body.storage_config_id is not None:
        storage = await session.get(StorageConfig, body.storage_config_id)
        if not storage or storage.is_deleted:
            return {"code": 400, "message": "存储配置不存在", "data": None}

    if body.notification_config_id is not None:
        notification = await session.get(NotificationConfig, body.notification_config_id)
        if not notification or notification.is_deleted:
            return {"code": 400, "message": "通知配置不存在", "data": None}

    for key, value in body.model_dump(exclude_none=True).items():
        setattr(task, key, value)

    await session.commit()
    return {"code": 0, "message": "ok", "data": {"id": task.id, "status": task.status}}


@router.delete("/{task_id}")
async def delete_task(task_id: int, session: AsyncSession = Depends(get_db)):
    """软删除任务实例。"""
    task = await session.get(TaskInstance, task_id)
    if not task or task.is_deleted:
        return {"code": 404, "message": "任务不存在", "data": None}

    task.is_deleted = True
    await session.commit()
    return {"code": 0, "message": "ok", "data": {"id": task_id}}


@router.post("/{task_id}/run")
async def trigger_run(task_id: int, session: AsyncSession = Depends(get_db)):
    """
    手动触发任务执行。
    创建运行记录后，在后台异步调用 DrissionPage 适配器执行采集。
    """
    task = await session.get(TaskInstance, task_id)
    if not task or task.is_deleted:
        return {"code": 404, "message": "任务不存在", "data": None}

    run = TaskRun(
        task_id=task_id,
        trigger_type="manual",
        status="pending",
        started_at=datetime.now(),
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    # 异步执行任务（不阻塞 API 响应）
    from application.services.task_executor import execute_task_run
    from config.database import async_session_factory

    async def _run_in_background(run_id: int):
        """在独立会话中执行任务，避免和请求会话冲突。"""
        async with async_session_factory() as bg_session:
            await execute_task_run(bg_session, run_id)

    asyncio.create_task(_run_in_background(run.id))

    return {
        "code": 0,
        "message": "ok",
        "data": {"task_id": task_id, "run_id": run.id, "queued": True},
    }


@router.post("/{task_id}/retry")
async def retry_last_failed(task_id: int, session: AsyncSession = Depends(get_db)):
    """重试最近一次失败的执行。"""
    stmt = (
        select(TaskRun)
        .where(TaskRun.task_id == task_id, TaskRun.status == "failed")
        .order_by(TaskRun.started_at.desc())
        .limit(1)
    )
    last_failed = (await session.execute(stmt)).scalar_one_or_none()
    if not last_failed:
        return {"code": 400, "message": "没有可重试的失败记录", "data": None}

    run = TaskRun(
        task_id=task_id,
        trigger_type="retry",
        status="pending",
        retry_count=last_failed.retry_count + 1,
        started_at=datetime.now(),
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    # 异步执行重试任务（与手动执行保持一致）
    from application.services.task_executor import execute_task_run
    from config.database import async_session_factory

    async def _run_in_background(run_id: int):
        async with async_session_factory() as bg_session:
            await execute_task_run(bg_session, run_id)

    asyncio.create_task(_run_in_background(run.id))

    return {
        "code": 0,
        "message": "ok",
        "data": {"task_id": task_id, "run_id": run.id, "queued": True},
    }

