"""
取数指令：douyin/new_app
用途：
1. 聚焦页面取数动作，不处理登录和上传逻辑。
2. 按统一返回格式输出行数据，交由应用层统一上传。
"""

from __future__ import annotations

from typing import Any

from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.collect_instructions.base_collect_instruction import BaseCollectInstruction


class NewAppCollectInstruction(BaseCollectInstruction):
    """页面取数指令骨架。"""

    async def run(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        取数逻辑入口。
        说明：
        1. 可通过 context["page_getter"] 获取隔离浏览器页面对象并操作页面。
        2. 建议使用 execution_context.start_date/end_date 作为日期范围。
        """
        _ = context
        _ = execution_context
        _ = app_params
        return []
