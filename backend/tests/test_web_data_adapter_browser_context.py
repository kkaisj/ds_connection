"""
BaseWebDataAdapter 浏览器上下文解析测试
用途：验证 get_web_page 会按“显式参数 -> app_params -> ExecutionContext.extra -> 默认值”解析隔离键。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import infrastructure.connectors.base.isolated_browser as isolated_browser_module
from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.base.isolated_browser import IsolatedBrowserManager
from infrastructure.connectors.base.web_data_adapter import BaseWebDataAdapter


class _FakePage:
    """测试用页面对象，模拟 DrissionPage 的最小接口。"""

    def __init__(self) -> None:
        self.title = "ok"
        self.url = ""

    def get(self, url: str) -> None:
        self.url = url

    def quit(self) -> None:
        self.title = ""


class _DemoAdapter(BaseWebDataAdapter):
    """最小实现，用于测试基类通用能力。"""

    adapter_key = "demo.ctx_test"

    async def collect_rows(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        _ = context
        _ = execution_context
        _ = app_params
        return []


def _build_context(extra: dict[str, Any] | None = None) -> ExecutionContext:
    return ExecutionContext(
        run_id=1,
        task_id=2,
        adapter_key="demo.ctx_test",
        credentials={"username": "tester"},
        default_download_days=1,
        start_date="2026-04-10",
        end_date="2026-04-10",
        trace_id="run-1",
        extra=extra or {},
    )


def test_get_web_page_uses_context_extra_when_no_override() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        adapter = _DemoAdapter()
        manager = IsolatedBrowserManager(base_dir=Path(tmp), page_factory=lambda *_: _FakePage())
        old_manager = isolated_browser_module._MANAGER
        isolated_browser_module._MANAGER = manager
        ctx = _build_context(
            {
                "company_name": "CompA",
                "platform_code": "douyin",
                "account_name": "shop_01",
                "browser_zoom": "100",
            }
        )
        try:
            page = adapter.get_web_page(ctx, start_url="https://www.baidu.com")
            dump = manager.dump_sessions()
            assert page is not None
            assert "CompA" in dump
            assert "douyin_shop_01" in dump
        finally:
            isolated_browser_module._MANAGER = old_manager


def test_get_web_page_prefers_app_params_over_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        adapter = _DemoAdapter()
        manager = IsolatedBrowserManager(base_dir=Path(tmp), page_factory=lambda *_: _FakePage())
        old_manager = isolated_browser_module._MANAGER
        isolated_browser_module._MANAGER = manager
        ctx = _build_context(
            {"company_name": "OldComp", "platform_code": "old", "account_name": "old"}
        )
        try:
            first = adapter.get_web_page(
                ctx,
                app_params={
                    "company_name": "NewComp",
                    "platform_code": "taobao",
                    "account_name": "shopA",
                },
            )
            second = adapter.get_web_page(
                ctx,
                app_params={
                    "company_name": "NewComp",
                    "platform_code": "taobao",
                    "account_name": "shopA",
                },
            )
            dump = manager.dump_sessions()
            assert first is second
            assert "NewComp" in dump
            assert "taobao_shopA" in dump
            assert "OldComp" not in dump
        finally:
            isolated_browser_module._MANAGER = old_manager
