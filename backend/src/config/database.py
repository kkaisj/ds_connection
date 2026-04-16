from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config.settings import settings

engine = create_async_engine(settings.database_url, echo=settings.debug, pool_pre_ping=True)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session_factory() as session:
        yield session


async def dispose_database_engine() -> None:
    """
    关闭异步数据库连接池。
    用途：
    1. 在应用 shutdown/reload 时显式回收连接；
    2. 避免事件循环关闭后 aiomysql 在 __del__ 中被动清理导致告警。
    """
    await engine.dispose()

