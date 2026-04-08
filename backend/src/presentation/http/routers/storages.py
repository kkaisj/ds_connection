"""
存储管理路由层
提供存储配置的增删改查接口，删除为软删除。
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from infrastructure.persistence.models.models import StorageConfig

router = APIRouter()


class CreateStorageBody(BaseModel):
    """创建存储配置的请求参数"""
    type: str
    name: str
    config: dict


class UpdateStorageBody(BaseModel):
    """更新存储配置的请求参数"""
    name: str | None = None
    config: dict | None = None
    status: str | None = None


@router.get("")
async def list_storages(session: AsyncSession = Depends(get_db)):
    """查询未删除的存储配置列表。"""
    stmt = select(StorageConfig).where(StorageConfig.is_deleted == False).order_by(StorageConfig.id)
    result = await session.execute(stmt)

    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": s.id,
                "type": s.type,
                "name": s.name,
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in result.scalars().all()
        ],
    }


@router.post("")
async def create_storage(body: CreateStorageBody, session: AsyncSession = Depends(get_db)):
    """新增存储配置。"""
    storage = StorageConfig(type=body.type, name=body.name, config_enc=str(body.config).encode("utf-8"))
    session.add(storage)
    await session.commit()
    await session.refresh(storage)
    return {"code": 0, "message": "ok", "data": {"id": storage.id, "name": storage.name}}


@router.patch("/{storage_id}")
async def update_storage(storage_id: int, body: UpdateStorageBody, session: AsyncSession = Depends(get_db)):
    """更新存储配置。"""
    storage = await session.get(StorageConfig, storage_id)
    if not storage or storage.is_deleted:
        return {"code": 404, "message": "存储配置不存在", "data": None}

    if body.name is not None:
        storage.name = body.name
    if body.config is not None:
        storage.config_enc = str(body.config).encode("utf-8")
    if body.status is not None:
        storage.status = body.status

    await session.commit()
    return {"code": 0, "message": "ok", "data": {"id": storage.id, "status": storage.status}}


@router.delete("/{storage_id}")
async def delete_storage(storage_id: int, session: AsyncSession = Depends(get_db)):
    """软删除存储配置。"""
    storage = await session.get(StorageConfig, storage_id)
    if not storage or storage.is_deleted:
        return {"code": 404, "message": "存储配置不存在", "data": None}

    storage.is_deleted = True
    await session.commit()
    return {"code": 0, "message": "ok", "data": {"id": storage_id}}

