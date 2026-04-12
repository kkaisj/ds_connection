"""
工作台应用最小测试：pinduoduo/new_app
用途：
1. 验证应用文件可导入。
"""

from __future__ import annotations

import importlib


def test_import_app_main() -> None:
    """最小可用性测试。"""
    module_name = "infrastructure.connectors.pinduoduo.new_app"
    mod = importlib.import_module(module_name)
    assert mod is not None
