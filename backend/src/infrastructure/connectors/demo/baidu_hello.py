"""
演示适配器：百度搜索“你好”
用途：
1. 演示“登录指令集 + 取数指令集 + 统一上传入口”的完整编排方式。
2. 作为已上架 demo 应用，验证从发版到运行的最小闭环链路。
"""

from __future__ import annotations

from typing import Any

from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.base.web_data_adapter import BaseWebDataAdapter
from infrastructure.connectors.collect_instructions.demo.baidu_search_collect import (
    DemoBaiduSearchCollectInstruction,
)
from infrastructure.connectors.login_instructions.demo.baidu_noop_login import (
    DemoBaiduNoopLoginInstruction,
)


class DemoBaiduHelloAdapter(BaseWebDataAdapter):
    """
    百度“你好”演示适配器。
    核心逻辑：
    1. `ensure_login()` 调用登录指令集。
    2. `collect_rows()` 调用取数指令集。
    3. 适配器自身只负责参数编排，不写具体页面操作细节。
    """

    adapter_key = "demo.baidu_hello"

    def __init__(self) -> None:
        super().__init__()
        self._login_instruction = DemoBaiduNoopLoginInstruction()
        self._collect_instruction = DemoBaiduSearchCollectInstruction()

    async def create_context(
        self,
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        构建任务上下文。
        约定：通过 `page_getter` 暴露隔离浏览器获取能力，供取数指令复用。
        """
        keyword = str(app_params.get("keyword") or "你好")
        real_browser = bool(app_params.get("real_browser", False))

        def page_getter(start_url: str):
            """统一获取隔离浏览器页面对象。"""
            return self.get_web_page(
                execution_context,
                start_url=start_url,
                app_params=app_params,
            )

        return {
            "keyword": keyword,
            "real_browser": real_browser,
            "start_date": execution_context.start_date,
            "end_date": execution_context.end_date,
            "page_getter": page_getter,
        }

    async def ensure_login(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> None:
        """执行登录指令。"""
        await self._login_instruction.run(context, execution_context, app_params)

    async def collect_rows(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """执行取数指令并返回标准化数据。"""
        return await self._collect_instruction.run(context, execution_context, app_params)

