"""
登录指令：douyin/new_app
用途：
1. 封装平台登录动作，供多个取数应用复用。
2. 当前为骨架实现，后续按页面元素补齐具体登录步骤。
"""

from __future__ import annotations

from typing import Any

from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.login.base_login_instruction import BaseLoginInstruction


class NewAppLoginInstruction(BaseLoginInstruction):
    """平台登录指令骨架。"""

    async def run(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> None:
        """
        登录逻辑入口。
        说明：
        1. 可通过 context["page_getter"] 获取隔离浏览器页面对象。
        2. 可通过 execution_context.credentials 读取账号密码。
        """
        _ = context
        _ = execution_context
        _ = app_params
        return None
