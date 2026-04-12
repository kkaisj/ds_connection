"""
百度演示取数指令
用途：执行“打开百度 -> 输入关键词 -> 搜索”的取数动作，输出标准化结果。
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.collect_instructions.base_collect_instruction import (
    BaseCollectInstruction,
)


class DemoBaiduSearchCollectInstruction(BaseCollectInstruction):
    """
    百度演示取数指令。
    职责：
    1. 支持模拟模式（默认）用于联调。
    2. 支持真实浏览器模式用于端到端演示。
    """

    async def run(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        keyword = str(context.get("keyword") or "你好")
        real_browser = bool(context.get("real_browser", False))
        if real_browser:
            ok, msg = await self._run_real_browser(context, keyword)
            if not ok:
                raise RuntimeError(f"DRISSIONPAGE_NOT_READY: {msg}")

        # 模拟步骤：保证未启用真实浏览器时也可跑通完整链路。
        await asyncio.sleep(0.2)
        await asyncio.sleep(0.2)
        await asyncio.sleep(0.2)

        now = datetime.now().isoformat(timespec="seconds")
        _ = app_params
        return [
            {
                "数据集": "演示_百度搜索_你好",
                "文件路径": "",
                "待插入字段": [
                    [
                        "RPA日期",
                        "RPA关键词",
                        "RPA执行模式",
                        "RPA执行时间",
                        "RPA操作人",
                        "RPA开始日期",
                        "RPA结束日期",
                    ],
                    [
                        str(context.get("end_date") or ""),
                        keyword,
                        "real_browser" if real_browser else "simulated",
                        now,
                        str(execution_context.credentials.get("username", "")),
                        str(context.get("start_date") or ""),
                        str(context.get("end_date") or ""),
                    ],
                ],
                "去重主键": ["RPA日期", "RPA关键词", "RPA执行模式"],
            }
        ]

    async def _run_real_browser(self, context: dict[str, Any], keyword: str) -> tuple[bool, str]:
        """
        真实浏览器执行分支。
        通过 context 传入的 page_getter 获取隔离浏览器页面对象，避免指令耦合适配器实现。
        """
        page_getter = context.get("page_getter")
        if not callable(page_getter):
            return False, "缺少 page_getter，无法获取隔离浏览器页面对象"

        try:
            get_page: Callable[[str], Any] = page_getter  # type: ignore[assignment]
            page = get_page("https://www.baidu.com")
        except Exception as e:  # pragma: no cover
            return False, f"环境隔离浏览器初始化失败: {e}"

        try:
            box = page.ele("css:#kw")
            if not box:
                return False, "未找到百度搜索输入框 #kw"
            box.input(keyword)
            btn = page.ele("css:#su")
            if not btn:
                return False, "未找到百度搜索按钮 #su"
            btn.click()
            await asyncio.sleep(1.0)
            return True, "ok"
        except Exception as e:  # pragma: no cover
            return False, f"真实浏览器执行失败: {e}"
