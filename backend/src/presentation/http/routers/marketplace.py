"""
连接市场路由层
提供连接应用查询、上架和管理接口。
"""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, conint
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from infrastructure.connectors.base.registry import (
    get_adapter_meta,
    list_registered_adapter_templates,
)
from infrastructure.persistence.models.models import ConnectorApp, Platform, TaskInstance

router = APIRouter()


class CreateConnectorAppRequest(BaseModel):
    """上架应用请求体。"""

    platform_code: str = Field(..., description="平台编码，如 taobao/jd/pdd/douyin")
    name: str = Field(..., min_length=1, max_length=128, description="应用名称")
    adapter_key: str = Field(..., max_length=128, description="系统标识")
    version: str = Field("1.0.0", max_length=64, description="应用版本")
    description: str | None = Field(None, max_length=500, description="应用描述")
    status: Literal["active", "inactive"] = Field("active", description="状态：active/inactive")
    is_published: bool = Field(True, description="是否上架")
    avg_runtime_minutes: conint(ge=1, le=1440) = Field(6, description="平均运行时长（分钟）")
    ops_owner: str = Field("", max_length=128, description="运维人员")
    need_extra_params: bool = Field(False, description="是否需要额外参数")
    recommendation: conint(ge=1, le=5) = Field(3, description="推荐程度 1-5")
    platform_preview_url: str | None = Field(None, max_length=500, description="平台预览图地址")
    data_table: str = Field("", max_length=256, description="数据表格")
    collect_cycle: str = Field("", max_length=128, description="采集周期")
    metrics: str = Field("", max_length=500, description="指标")
    usage_guide: str = Field("", max_length=2000, description="使用说明")


class UpdateConnectorAppRequest(BaseModel):
    """应用管理编辑请求体。"""

    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=500)
    status: Literal["active", "inactive"] | None = Field(None)
    is_published: bool | None = Field(None)
    avg_runtime_minutes: conint(ge=1, le=1440) | None = Field(None)
    ops_owner: str | None = Field(None, max_length=128)
    need_extra_params: bool | None = Field(None)
    recommendation: conint(ge=1, le=5) | None = Field(None)
    platform_preview_url: str | None = Field(None, max_length=500)
    data_table: str | None = Field(None, max_length=256)
    collect_cycle: str | None = Field(None, max_length=128)
    metrics: str | None = Field(None, max_length=500)
    usage_guide: str | None = Field(None, max_length=2000)


def _extract_app_meta(app: ConnectorApp) -> dict:
    """统一提取应用扩展信息。"""
    meta = app.param_schema or {}
    return {
        "is_published": bool(meta.get("is_published", app.status == "active")),
        "avg_runtime_minutes": int(meta.get("avg_runtime_minutes", 6) or 6),
        "ops_owner": str(meta.get("ops_owner", "") or ""),
        "need_extra_params": bool(meta.get("need_extra_params", False)),
        "recommendation": int(meta.get("recommendation", 3) or 3),
        "platform_preview_url": meta.get("platform_preview_url"),
        "data_table": str(meta.get("data_table", "") or ""),
        "collect_cycle": str(meta.get("collect_cycle", "") or ""),
        "metrics": str(meta.get("metrics", "") or ""),
        "usage_guide": str(meta.get("usage_guide", "") or ""),
    }


@router.post("")
async def create_app(payload: CreateConnectorAppRequest, session: AsyncSession = Depends(get_db)):
    """
    上架连接应用。

    规则：
    - 必须绑定已存在且未删除的平台
    - 平台内应用名不可重复（未删除范围）
    - adapter_key 必须已注册且未被上架
    """
    platform = await session.scalar(
        select(Platform).where(
            Platform.code == payload.platform_code,
            Platform.is_deleted == False,
        )
    )
    if not platform:
        return {"code": 400, "message": "平台不存在", "data": None}

    exists = await session.scalar(
        select(func.count())
        .select_from(ConnectorApp)
        .where(
            ConnectorApp.platform_id == platform.id,
            ConnectorApp.name == payload.name,
            ConnectorApp.is_deleted == False,
        )
    ) or 0
    if exists > 0:
        return {"code": 400, "message": "同平台下应用名称已存在", "data": None}

    adapter_key = payload.adapter_key.strip()
    adapter_meta = get_adapter_meta(adapter_key)
    if not adapter_meta:
        return {"code": 400, "message": "系统标识未注册", "data": None}

    if adapter_meta["platform_code"] != payload.platform_code:
        return {"code": 400, "message": "系统标识与平台不匹配", "data": None}

    key_exists = await session.scalar(
        select(func.count())
        .select_from(ConnectorApp)
        .where(
            ConnectorApp.adapter_key == adapter_key,
            ConnectorApp.is_deleted == False,
        )
    ) or 0
    if key_exists > 0:
        return {"code": 400, "message": "该应用模板已上架", "data": None}

    app = ConnectorApp(
        platform_id=platform.id,
        name=payload.name.strip(),
        adapter_key=adapter_key,
        version=payload.version.strip(),
        description=payload.description.strip() if payload.description else None,
        status="active" if payload.is_published else "inactive",
        param_schema={
            "is_published": payload.is_published,
            "avg_runtime_minutes": payload.avg_runtime_minutes,
            "ops_owner": payload.ops_owner.strip(),
            "need_extra_params": payload.need_extra_params,
            "recommendation": payload.recommendation,
            "platform_preview_url": payload.platform_preview_url.strip() if payload.platform_preview_url else None,
            "data_table": payload.data_table.strip(),
            "collect_cycle": payload.collect_cycle.strip(),
            "metrics": payload.metrics.strip(),
            "usage_guide": payload.usage_guide.strip(),
        },
    )
    session.add(app)
    await session.commit()
    await session.refresh(app)

    meta = _extract_app_meta(app)
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "id": app.id,
            "name": app.name,
            "version": app.version,
            "status": app.status,
            "platform_code": platform.code,
            "platform_name": platform.name,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            **meta,
        },
    }


@router.get("/available-adapters")
async def list_available_adapters(session: AsyncSession = Depends(get_db)):
    """查询已开发应用模板（按系统标识注册），并标记是否已上架。"""
    templates = list_registered_adapter_templates()

    rows = (
        await session.execute(
            select(
                ConnectorApp.id,
                ConnectorApp.name,
                ConnectorApp.adapter_key,
                ConnectorApp.status,
            ).where(
                ConnectorApp.is_deleted == False,
                ConnectorApp.adapter_key.is_not(None),
            )
        )
    ).all()

    by_key: dict[str, list[dict]] = {}
    for app_id, app_name, adapter_key, status in rows:
        if not adapter_key:
            continue
        by_key.setdefault(adapter_key, []).append(
            {
                "id": app_id,
                "name": app_name,
                "status": status,
            }
        )

    data = []
    for t in templates:
        listed_apps = by_key.get(t["adapter_key"], [])
        data.append(
            {
                "adapter_key": t["adapter_key"],
                "platform_code": t["platform_code"],
                "display_name": t["display_name"],
                "description": t["description"],
                "default_version": t["default_version"],
                "is_listed": len(listed_apps) > 0,
                "listed_apps": listed_apps,
            }
        )

    return {"code": 0, "message": "ok", "data": data}


@router.get("")
async def list_apps(
    platform: str | None = Query(None, description="按平台 code 筛选"),
    keyword: str | None = Query(None, description="按名称关键词搜索"),
    include_inactive: bool = Query(False, description="是否包含未上架应用"),
    session: AsyncSession = Depends(get_db),
):
    """
    查询连接应用列表。
    默认仅返回未删除且 active 的应用，应用管理可通过 include_inactive=true 查询全部。
    """
    stmt = (
        select(ConnectorApp, Platform)
        .join(Platform, ConnectorApp.platform_id == Platform.id)
        .where(ConnectorApp.is_deleted == False)
    )

    if not include_inactive:
        stmt = stmt.where(ConnectorApp.status == "active")
    if platform:
        stmt = stmt.where(Platform.code == platform)
    if keyword:
        stmt = stmt.where(ConnectorApp.name.contains(keyword))

    stmt = stmt.order_by(ConnectorApp.id)
    result = await session.execute(stmt)

    items = []
    for app, plat in result.all():
        meta = _extract_app_meta(app)
        items.append(
            {
                "id": app.id,
                "name": app.name,
                "description": app.description,
                "version": app.version,
                "status": app.status,
                "platform_code": plat.code,
                "platform_name": plat.name,
                "created_at": app.created_at.isoformat() if app.created_at else None,
                **meta,
            }
        )

    return {
        "code": 0,
        "message": "ok",
        "data": items,
    }


@router.get("/platforms")
async def list_platforms(session: AsyncSession = Depends(get_db)):
    """查询所有未删除的平台列表，包含父子层级信息。"""
    stmt = select(Platform).where(Platform.is_deleted == False).order_by(Platform.id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    id_set = {p.id for p in rows}

    data = []
    for p in rows:
        parent_id = p.parent_id if p.parent_id in id_set else None
        level = 1 if parent_id is None else 2
        data.append(
            {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "parent_id": parent_id,
                "level": level,
            }
        )

    return {
        "code": 0,
        "message": "ok",
        "data": data,
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
    task_count = (
        await session.scalar(
            select(func.count())
            .select_from(TaskInstance)
            .where(TaskInstance.app_id == app_id, TaskInstance.is_deleted == False)
        )
        or 0
    )

    meta = _extract_app_meta(app)
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
            **meta,
        },
    }


@router.patch("/{app_id}")
async def update_app(app_id: int, payload: UpdateConnectorAppRequest, session: AsyncSession = Depends(get_db)):
    """编辑应用管理信息。"""
    app = await session.get(ConnectorApp, app_id)
    if not app or app.is_deleted:
        return {"code": 404, "message": "应用不存在", "data": None}

    platform = await session.scalar(
        select(Platform).where(Platform.id == app.platform_id, Platform.is_deleted == False)
    )
    if not platform:
        return {"code": 400, "message": "平台不存在", "data": None}

    if payload.name is not None:
        app.name = payload.name.strip()
    if payload.description is not None:
        app.description = payload.description.strip() or None

    meta = app.param_schema or {}
    update_map = payload.model_dump(exclude_unset=True)
    for key in (
        "is_published",
        "avg_runtime_minutes",
        "ops_owner",
        "need_extra_params",
        "recommendation",
        "platform_preview_url",
        "data_table",
        "collect_cycle",
        "metrics",
        "usage_guide",
    ):
        if key in update_map:
            value = update_map[key]
            if isinstance(value, str):
                value = value.strip()
            meta[key] = value

    if payload.status is not None:
        app.status = payload.status
        meta["is_published"] = payload.status == "active"
    elif payload.is_published is not None:
        app.status = "active" if payload.is_published else "inactive"
        meta["is_published"] = payload.is_published

    app.param_schema = meta
    await session.commit()
    await session.refresh(app)

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "id": app.id,
            "name": app.name,
            "description": app.description,
            "version": app.version,
            "status": app.status,
            "platform_code": platform.code,
            "platform_name": platform.name,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            **_extract_app_meta(app),
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
