"""
应用生命周期测试。
用途：
1. 验证 FastAPI lifespan 可正常进入与退出；
2. 间接验证 shutdown 阶段可执行数据库连接池释放逻辑，不抛异常。
"""

from __future__ import annotations

import asyncio

from main import app


def test_app_lifespan_runs_without_error() -> None:
    """应用生命周期钩子应可正常执行。"""

    async def _run() -> None:
        async with app.router.lifespan_context(app):
            return None

    asyncio.run(_run())
