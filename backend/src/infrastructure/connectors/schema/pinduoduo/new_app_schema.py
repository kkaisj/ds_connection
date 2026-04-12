"""
输入输出 schema：pinduoduo/new_app
用途：
1. 定义 input/output 结构，统一参数读取入口。
"""

from __future__ import annotations
from typing import Any


def build_input(credentials: dict[str, Any], app_params: dict[str, Any]) -> dict[str, Any]:
    """构建统一 input 对象。"""
    return {
        "credentials": credentials,
        "page_params": dict(app_params.get("page_params") or {}),
        "default_download_days": int(app_params.get("default_download_days") or 1),
        "runtime": {
            "real_browser": bool(app_params.get("real_browser", True)),
        },
        "storage": dict(app_params.get("storage") or {}),
    }
