"""
连接市场路由层
提供连接应用的查询接口，支持按平台筛选和关键词搜索。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from infrastructure.persistence.models.models import ConnectorApp, Platform, TaskInstance

router = APIRouter()


@router.get("")
async def list_apps(
    platform: str | None = Query(None, description="按平台 code 筛选"),
    keyword: str | None = Query(None, description="按名称关键词搜索"),
    session: AsyncSession = Depends(get_db),
):
    """
    查询连接应用列表。
    仅返回未删除且 active 的应用。
    """
    stmt = (
        select(ConnectorApp, Platform)
        .join(Platform, ConnectorApp.platform_id == Platform.id)
        .where(ConnectorApp.status == "active", ConnectorApp.is_deleted == False)
    )

    if platform:
        stmt = stmt.where(Platform.code == platform)
    if keyword:
        stmt = stmt.where(ConnectorApp.name.contains(keyword))

    stmt = stmt.order_by(ConnectorApp.id)
    result = await session.execute(stmt)

    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": app.id,
                "name": app.name,
                "description": app.description,
                "version": app.version,
                "status": app.status,
                "platform_code": plat.code,
                "platform_name": plat.name,
                "created_at": app.created_at.isoformat() if app.created_at else None,
            }
            for app, plat in result.all()
        ],
    }


@router.get("/platforms")
async def list_platforms(session: AsyncSession = Depends(get_db)):
    """查询所有未删除的平台列表，用于前端筛选器。"""
    stmt = select(Platform).where(Platform.is_deleted == False).order_by(Platform.id)
    result = await session.execute(stmt)

    return {
        "code": 0,
        "message": "ok",
        "data": [
            {"id": p.id, "code": p.code, "name": p.name}
            for p in result.scalars().all()
        ],
    }


@router.get("/{app_id}")
async def get_app_detail(app_id: int, session: AsyncSession = Depends(get_db)):
    """查询单个连接应用详情，包含关联任务数量。"""
    stmt = (
        select(ConnectorApp, Platform)
        .join(Platform, ConnectorApp.platform_id == Platform.id)
        .where(ConnectorApp.id == app_id, ConnectorApp.is_deleted == False)
    )
    row = (await session.execute(stmt)).first()

    if not row:
        return {"code": 404, "message": "应用不存在", "data": None}

    app, plat = row
    task_count = await session.scalar(
        select(func.count()).select_from(TaskInstance)
        .where(TaskInstance.app_id == app_id, TaskInstance.is_deleted == False)
    ) or 0

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "id": app.id,
            "name": app.name,
            "description": app.description,
            "version": app.version,
            "status": app.status,
            "param_schema": app.param_schema,
            "platform_code": plat.code,
            "platform_name": plat.name,
            "task_count": task_count,
            "created_at": app.created_at.isoformat() if app.created_at else None,
        },
    }


@router.delete("/{app_id}")
async def delete_app(app_id: int, session: AsyncSession = Depends(get_db)):
    """软删除连接应用。"""
    app = await session.get(ConnectorApp, app_id)
    if not app or app.is_deleted:
        return {"code": 404, "message": "应用不存在", "data": None}

    app.is_deleted = True
    await session.commit()
    return {"code": 0, "message": "ok", "data": {"id": app_id}}

