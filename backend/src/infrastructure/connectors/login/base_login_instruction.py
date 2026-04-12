"""
登录指令集基类
用途：定义统一的“平台登录指令”接口，所有平台登录逻辑都放在指令集内复用。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from infrastructure.connectors.base.execution_context import ExecutionContext


class BaseLoginInstruction(ABC):
    """
    登录指令统一抽象。
    职责：
    1. 接收任务级上下文（凭据、日期范围、隔离浏览器参数）。
    2. 执行平台登录步骤（打开登录页、输入账密、登录态校验等）。
    """

    @abstractmethod
    async def run(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> None:
        """执行登录指令。"""
        raise NotImplementedError

