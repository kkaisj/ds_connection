"""
取数指令集基类
用途：定义统一的“页面取数指令”接口，平台页面取数逻辑按指令拆分复用。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from infrastructure.connectors.base.execution_context import ExecutionContext


class BaseCollectInstruction(ABC):
    """
    取数指令统一抽象。
    职责：
    1. 在已完成登录的前提下执行页面取数流程。
    2. 返回标准化行数据，供应用层统一上传/入库。
    """

    @abstractmethod
    async def run(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """执行取数指令并返回行数据。"""
        raise NotImplementedError

