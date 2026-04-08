"""
账号管理路由层
提供店铺账号的增删改查接口。
敏感字段脱敏展示，支持验证码转发配置（可选）。
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from infrastructure.persistence.models.models import Platform, ShopAccount

router = APIRouter()


class CreateAccountBody(BaseModel):
    """创建店铺账号的请求参数"""
    platform_id: int
    shop_name: str
    username: str
    password: str
    extra: dict | None = None
    # 验证码转发（可选）
    captcha_method: str = "none"   # none / sms_forward / email_forward / email_auth_code / manual
    captcha_config: dict | None = None
    captcha_enabled: bool = False


class UpdateAccountBody(BaseModel):
    """更新店铺账号的请求参数，所有字段可选"""
    shop_name: str | None = None
    password: str | None = None
    status: str | None = None
    extra: dict | None = None
    # 验证码转发
    captcha_method: str | None = None
    captcha_config: dict | None = None
    captcha_enabled: bool | None = None


def _mask(value: str) -> str:
    """脱敏处理：保留首尾字符，中间用 * 替代"""
    if len(value) <= 2:
        return value[0] + "*"
    return value[0] + "*" * (len(value) - 2) + value[-1]


@router.get("")
async def list_accounts(
    platform: str | None = Query(None, description="按平台 code 筛选"),
    status: str | None = Query(None, description="按状态筛选 active/inactive/disabled"),
    session: AsyncSession = Depends(get_db),
):
    """查询未删除的店铺账号列表，敏感信息脱敏，含验证码转发配置。"""
    stmt = (
        select(ShopAccount, Platform)
        .join(Platform, ShopAccount.platform_id == Platform.id)
        .where(ShopAccount.is_deleted == False)
    )

    if platform:
        stmt = stmt.where(Platform.code == platform)
    if status:
        stmt = stmt.where(ShopAccount.status == status)

    stmt = stmt.order_by(ShopAccount.id)
    result = await session.execute(stmt)

    return {
        "code": 0,
        "message": "ok",
        "data": [
            {
                "id": acc.id,
                "shop_name": acc.shop_name,
                "username_masked": _mask(acc.username_enc.decode("utf-8", errors="replace")),
                "status": acc.status,
                "health_score": acc.health_score,
                "platform_code": plat.code,
                "platform_name": plat.name,
                "captcha_method": acc.captcha_method,
                "captcha_config": acc.captcha_config,
                "captcha_enabled": acc.captcha_enabled,
                "created_at": acc.created_at.isoformat() if acc.created_at else None,
            }
            for acc, plat in result.all()
        ],
    }


@router.post("")
async def create_account(body: CreateAccountBody, session: AsyncSession = Depends(get_db)):
    """新增店铺账号，支持可选的验证码转发配置。"""
    account = ShopAccount(
        platform_id=body.platform_id,
        shop_name=body.shop_name,
        username_enc=body.username.encode("utf-8"),
        password_enc=body.password.encode("utf-8"),
        extra_enc=str(body.extra).encode("utf-8") if body.extra else None,
        captcha_method=body.captcha_method,
        captcha_config=body.captcha_config,
        captcha_enabled=body.captcha_enabled,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return {"code": 0, "message": "ok", "data": {"id": account.id, "shop_name": account.shop_name}}


@router.patch("/{account_id}")
async def update_account(account_id: int, body: UpdateAccountBody, session: AsyncSession = Depends(get_db)):
    """更新店铺账号信息，含验证码转发配置。"""
    account = await session.get(ShopAccount, account_id)
    if not account or account.is_deleted:
        return {"code": 404, "message": "账号不存在", "data": None}

    if body.shop_name is not None:
        account.shop_name = body.shop_name
    if body.password is not None:
        account.password_enc = body.password.encode("utf-8")
    if body.status is not None:
        account.status = body.status
    if body.extra is not None:
        account.extra_enc = str(body.extra).encode("utf-8")
    if body.captcha_method is not None:
        account.captcha_method = body.captcha_method
    if body.captcha_config is not None:
        account.captcha_config = body.captcha_config
    if body.captcha_enabled is not None:
        account.captcha_enabled = body.captcha_enabled

    await session.commit()
    return {"code": 0, "message": "ok", "data": {"id": account.id, "status": account.status}}


@router.delete("/{account_id}")
async def delete_account(account_id: int, session: AsyncSession = Depends(get_db)):
    """软删除店铺账号。"""
    account = await session.get(ShopAccount, account_id)
    if not account or account.is_deleted:
        return {"code": 404, "message": "账号不存在", "data": None}

    account.is_deleted = True
    await session.commit()
    return {"code": 0, "message": "ok", "data": {"id": account_id}}

