"""
连接任务路由层
提供任务实例的增删改查、手动执行和重试接口。
所有查询过滤 is_deleted=False，删除操作为软删除。
"""

import asyncio
import ast
import json
from datetime import datetime
from typing import Any

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


class UpdateTaskSidebarParamsBody(BaseModel):
    """任务侧边栏参数保存请求体。"""

    default_download_days: int = 1
    extra_params: dict[str, Any] | None = None


class UpdateTaskSidebarStorageBody(BaseModel):
    """任务侧边栏存储配置保存请求体。"""

    storage_config_id: int


def _decode_storage_config(config_enc: bytes) -> dict[str, Any]:
    """解析 storage_config.config_enc，兼容 json 与历史 str(dict)。"""
    raw = (config_enc or b"").decode("utf-8", errors="replace").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        pass
    try:
        value = ast.literal_eval(raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


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


@router.get("/{task_id}/sidebar")
async def get_task_sidebar_data(task_id: int, session: AsyncSession = Depends(get_db)):
    """
    获取任务右侧侧边栏联动数据。
    返回：
    1. 任务参数草稿（default_download_days + extra_params）
    2. 当前存储配置 + 可选存储列表
    3. 最近执行记录（倒序）及默认选中批次日志
    """
    task = await session.get(TaskInstance, task_id)
    if not task or task.is_deleted:
        return {"code": 404, "message": "任务不存在", "data": None}

    params = dict(task.params or {})
    default_download_days = max(int(params.get("default_download_days", 1) or 1), 1)
    extra_params = dict(params)
    extra_params.pop("default_download_days", None)

    current_storage = await session.get(StorageConfig, task.storage_config_id)
    storage_stmt = (
        select(StorageConfig)
        .where(StorageConfig.is_deleted.is_(False))
        .order_by(StorageConfig.id.desc())
    )
    storage_rows = (await session.execute(storage_stmt)).scalars().all()
    storage_options = [
        {"id": s.id, "name": s.name, "type": s.type, "status": s.status} for s in storage_rows
    ]

    run_stmt = (
        select(TaskRun)
        .where(TaskRun.task_id == task.id)
        .order_by(TaskRun.started_at.desc(), TaskRun.id.desc())
        .limit(20)
    )
    runs = (await session.execute(run_stmt)).scalars().all()
    run_items = [
        {
            "id": r.id,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "ended_at": r.ended_at.isoformat() if r.ended_at else None,
            "duration_ms": r.duration_ms,
            "error_code": r.error_code,
            "error_message": r.error_message,
        }
        for r in runs
    ]

    selected_run_id = run_items[0]["id"] if run_items else None
    log_items: list[dict[str, Any]] = []
    if selected_run_id is not None:
        log_stmt = (
            select(TaskRunLog)
            .where(TaskRunLog.run_id == selected_run_id)
            .order_by(TaskRunLog.created_at)
        )
        log_rows = (await session.execute(log_stmt)).scalars().all()
        log_items = [
            {
                "step": log.step,
                "level": log.level,
                "message": log.message,
                "ext": log.ext,
                "ts": log.created_at.isoformat() if log.created_at else None,
            }
            for log in log_rows
        ]

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "task_id": task.id,
            "params": {
                "default_download_days": default_download_days,
                "extra_params": extra_params,
            },
            "storage": {
                "current_storage_id": task.storage_config_id,
                "current_storage": {
                    "id": current_storage.id,
                    "name": current_storage.name,
                    "type": current_storage.type,
                    "status": current_storage.status,
                    "config": _decode_storage_config(current_storage.config_enc),
                }
                if current_storage
                else None,
                "options": storage_options,
            },
            "logs": {
                "runs": run_items,
                "selected_run_id": selected_run_id,
                "items": log_items,
            },
        },
    }


@router.patch("/{task_id}/sidebar/params")
async def update_task_sidebar_params(
    task_id: int,
    body: UpdateTaskSidebarParamsBody,
    session: AsyncSession = Depends(get_db),
):
    """保存侧边栏参数配置。"""
    task = await session.get(TaskInstance, task_id)
    if not task or task.is_deleted:
        return {"code": 404, "message": "任务不存在", "data": None}

    days = max(int(body.default_download_days or 1), 1)
    extra = dict(body.extra_params or {})
    extra["default_download_days"] = days
    task.params = extra
    await session.commit()

    return {"code": 0, "message": "ok", "data": {"task_id": task.id, "params": task.params}}


@router.patch("/{task_id}/sidebar/storage")
async def update_task_sidebar_storage(
    task_id: int,
    body: UpdateTaskSidebarStorageBody,
    session: AsyncSession = Depends(get_db),
):
    """保存侧边栏存储配置。"""
    task = await session.get(TaskInstance, task_id)
    if not task or task.is_deleted:
        return {"code": 404, "message": "任务不存在", "data": None}

    storage = await session.get(StorageConfig, body.storage_config_id)
    if not storage or storage.is_deleted:
        return {"code": 400, "message": "存储配置不存在", "data": None}

    task.storage_config_id = body.storage_config_id
    await session.commit()
    return {"code": 0, "message": "ok", "data": {"task_id": task.id, "storage_config_id": task.storage_config_id}}


@router.get("/{task_id}/sidebar/logs")
async def get_task_sidebar_logs(
    task_id: int,
    run_id: int,
    session: AsyncSession = Depends(get_db),
):
    """获取任务侧边栏指定执行批次日志。"""
    task = await session.get(TaskInstance, task_id)
    if not task or task.is_deleted:
        return {"code": 404, "message": "任务不存在", "data": None}

    run = await session.get(TaskRun, run_id)
    if not run or run.task_id != task_id:
        return {"code": 404, "message": "执行记录不存在", "data": None}

    stmt = (
        select(TaskRunLog)
        .where(TaskRunLog.run_id == run_id)
        .order_by(TaskRunLog.created_at)
    )
    logs = (await session.execute(stmt)).scalars().all()
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "task_id": task_id,
            "run_id": run_id,
            "items": [
                {
                    "step": log.step,
                    "level": log.level,
                    "message": log.message,
                    "ext": log.ext,
                    "ts": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        },
    }

