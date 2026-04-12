"""
应用适配器：pinduoduo/new_app
用途：
1. 作为“登录 + 取数 + 上传”链路中的编排层。
2. 登录和取数逻辑分别复用指令集，适配器只负责参数组织和调用。
"""

from __future__ import annotations

from typing import Any

from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.base.web_data_adapter import BaseWebDataAdapter
from infrastructure.connectors.collect_instructions.pinduoduo.new_app_collect import NewAppCollectInstruction
from infrastructure.connectors.login_instructions.pinduoduo.new_app_login import NewAppLoginInstruction


class NewAppAdapter(BaseWebDataAdapter):
    """应用适配器编排骨架。"""

    adapter_key = "pinduoduo.new_app"

    def __init__(self) -> None:
        super().__init__()
        self._login_instruction = NewAppLoginInstruction()
        self._collect_instruction = NewAppCollectInstruction()

    async def create_context(
        self,
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        构建运行上下文。
        说明：
        1. 统一暴露 page_getter，供登录/取数指令复用隔离浏览器。
        2. 可在此注入业务参数，如店铺、报表维度等。
        """
        def page_getter(start_url: str):
            return self.get_web_page(
                execution_context,
                start_url=start_url,
                app_params=app_params,
            )

        return {
            "page_getter": page_getter,
            "start_date": execution_context.start_date,
            "end_date": execution_context.end_date,
        }

    async def ensure_login(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> None:
        """调用登录指令。"""
        await self._login_instruction.run(context, execution_context, app_params)

    async def collect_rows(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """调用取数指令并返回标准化行数据。"""
        return await self._collect_instruction.run(context, execution_context, app_params)
