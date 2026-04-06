"""
消息通知路由层
提供通知配置的增删改查接口，删除为软删除。
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dc_backend.config.database import get_db
from dc_backend.infrastructure.persistence.models.models import NotificationConfig

router = APIRouter()


class CreateNotificationBody(BaseModel):
    """创建通知配置的请求参数"""
    channel: str
    webhook_url: str
    notify_on_fail: bool = True
    notify_on_retry_fail: bool = True
    notify_on_account_invalid: bool = True
    dedupe_window_sec: int = 300
    rate_limit_per_min: int = 20


class UpdateNotificationBody(BaseModel):
    """更新通知配置的请求参数"""
    webhook_url: str | None = None
    notify_on_fail: bool | None = None
    notify_on_retry_fail: bool | None = None
    notify_on_account_invalid: bool | None = None
    dedupe_window_sec: int | None = None
    rate_limit_per_min: int | None = None
    status: str | None = None


@router.get("")
async def list_notifications(session: AsyncSession = Depends(get_db)):
    """查询未删除的通知配置列表。"""
    stmt = select(NotificationConfig).where(NotificationConfig.is_deleted == False).order_by(NotificationConfig.id)
    result = await session.execute(stmt)

    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": n.id,
                "channel": n.channel,
                "notify_on_fail": bool(n.notify_on_fail),
                "notify_on_retry_fail": bool(n.notify_on_retry_fail),
                "notify_on_account_invalid": bool(n.notify_on_account_invalid),
                "dedupe_window_sec": n.dedupe_window_sec,
                "rate_limit_per_min": n.rate_limit_per_min,
                "status": n.status,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in result.scalars().all()
        ],
    }


@router.post("")
async def create_notification(body: CreateNotificationBody, session: AsyncSession = Depends(get_db)):
    """新增通知配置，webhook_url 编码存储。"""
    config = NotificationConfig(
        channel=body.channel,
        webhook_url_enc=body.webhook_url.encode("utf-8"),
        notify_on_fail=body.notify_on_fail,
        notify_on_retry_fail=body.notify_on_retry_fail,
        notify_on_account_invalid=body.notify_on_account_invalid,
        dedupe_window_sec=body.dedupe_window_sec,
        rate_limit_per_min=body.rate_limit_per_min,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return {"code": 0, "message": "ok", "data": {"id": config.id, "channel": config.channel}}


@router.patch("/{config_id}")
async def update_notification(config_id: int, body: UpdateNotificationBody, session: AsyncSession = Depends(get_db)):
    """更新通知配置。"""
    config = await session.get(NotificationConfig, config_id)
    if not config or config.is_deleted:
        return {"code": 404, "message": "通知配置不存在", "data": None}

    if body.webhook_url is not None:
        config.webhook_url_enc = body.webhook_url.encode("utf-8")
    for field in ["notify_on_fail", "notify_on_retry_fail", "notify_on_account_invalid",
                   "dedupe_window_sec", "rate_limit_per_min", "status"]:
        val = getattr(body, field)
        if val is not None:
            setattr(config, field, val)

    await session.commit()
    return {"code": 0, "message": "ok", "data": {"id": config.id, "status": config.status}}


@router.delete("/{config_id}")
async def delete_notification(config_id: int, session: AsyncSession = Depends(get_db)):
    """软删除通知配置。"""
    config = await session.get(NotificationConfig, config_id)
    if not config or config.is_deleted:
        return {"code": 404, "message": "通知配置不存在", "data": None}

    config.is_deleted = True
    await session.commit()
    return {"code": 0, "message": "ok", "data": {"id": config_id}}
