"""
百度演示登录指令
用途：为 demo 场景提供统一登录入口（当前不需要真实登录，保留指令位）。
"""

from __future__ import annotations

from typing import Any

from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.login_instructions.base_login_instruction import BaseLoginInstruction


class DemoBaiduNoopLoginInstruction(BaseLoginInstruction):
    """
    百度演示登录指令。
    职责：
    1. 与真实平台保持一致的调用接口。
    2. 当前仅做 no-op，便于后续替换为真实登录流程。
    """

    async def run(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> None:
        _ = context
        _ = execution_context
        _ = app_params
        return None

