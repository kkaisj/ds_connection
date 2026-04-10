"""
演示适配器：百度搜索“你好”。

用途：
- 提供一条可用于“发版 -> 上架 -> 任务执行 -> 执行记录回流”的最小闭环链路
- 在未安装 DrissionPage 时，仍可走模拟执行，便于本地联调
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from infrastructure.connectors.base.adapter import AdapterResult, BaseAdapter


class DemoBaiduHelloAdapter(BaseAdapter):
    """演示适配器：打开百度，输入“你好”，按回车。"""

    adapter_key = "demo.baidu_hello"

    async def execute(
        self,
        credentials: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> AdapterResult:
        """
        执行演示自动化。

        参数说明：
        - params.keyword: 搜索词，默认“你好”
        - params.real_browser: 是否尝试真实浏览器执行（默认 false）
        """
        p = params or {}
        keyword = str(p.get("keyword") or "你好")
        real_browser = bool(p.get("real_browser", False))

        if real_browser:
            ok, msg = await self._try_drissionpage(keyword)
            if not ok:
                return AdapterResult(
                    success=False,
                    error_code="DRISSIONPAGE_NOT_READY",
                    error_message=msg,
                    rows_count=0,
                    data=[],
                )

        # 模拟执行步骤（保证在未安装浏览器自动化依赖时也能联调闭环）
        await asyncio.sleep(0.2)  # 打开页面
        await asyncio.sleep(0.2)  # 输入关键词
        await asyncio.sleep(0.2)  # 回车搜索

        now = datetime.now().isoformat(timespec="seconds")
        return AdapterResult(
            success=True,
            rows_count=1,
            data=[
                {
                    "action": "baidu_search",
                    "keyword": keyword,
                    "executed_at": now,
                    "mode": "real_browser" if real_browser else "simulated",
                    "note": "已执行“打开百度 -> 输入关键词 -> 回车”流程",
                }
            ],
        )

    async def _try_drissionpage(self, keyword: str) -> tuple[bool, str]:
        """尝试真实 DrissionPage 执行，失败时返回错误信息。"""
        try:
            from DrissionPage import ChromiumPage  # type: ignore
        except Exception as e:  # pragma: no cover
            return False, f"未安装 DrissionPage 或导入失败: {e}"

        try:
            page = ChromiumPage()
            page.get("https://www.baidu.com")
            box = page.ele('css:#kw')
            if not box:
                return False, "未找到百度搜索输入框 #kw"
            box.input(keyword)
            btn = page.ele('css:#su')
            if not btn:
                return False, "未找到百度搜索按钮 #su"
            btn.click()
            await asyncio.sleep(1.0)
            page.quit()
            return True, "ok"
        except Exception as e:  # pragma: no cover
            return False, f"真实浏览器执行失败: {e}"

