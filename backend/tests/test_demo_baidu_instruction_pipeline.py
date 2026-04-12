"""
百度演示适配器指令集编排测试
用途：验证 demo 适配器已迁移为“登录指令 + 取数指令”模式且可正常返回结果。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.demo.baidu_hello import DemoBaiduHelloAdapter


@pytest.mark.asyncio
async def test_demo_adapter_returns_rows_in_simulated_mode() -> None:
    """
    关键验证：
    1. 适配器在模拟模式可执行。
    2. 返回标准数据集对象字段，且执行模式符合预期。
    """
    adapter = DemoBaiduHelloAdapter()
    context = ExecutionContext(
        run_id=1,
        task_id=1,
        adapter_key=adapter.adapter_key,
        credentials={"username": "tester"},
        default_download_days=1,
        start_date="2026-04-10",
        end_date="2026-04-10",
        trace_id="run-1",
        extra={},
    )
    result = await adapter.execute_with_context(
        context,
        {"keyword": "你好", "real_browser": False},
    )
    assert result.success is True
    assert result.rows_count == 1
    row = result.data[0]
    assert row["数据集"] == "演示_百度搜索_你好"
    assert row["待插入字段"][1][2] == "simulated"
