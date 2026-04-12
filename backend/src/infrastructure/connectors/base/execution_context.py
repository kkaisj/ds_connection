"""
全局执行上下文对象
用途：沉淀任务执行的核心共用信息（账密、日期范围、运行元数据），
避免在每个页面取数实现中重复传参。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any


@dataclass
class ExecutionContext:
    """
    统一执行上下文。

    约定：
    1. 核心信息进全局对象（credentials/start_date/end_date/run 元数据）。
    2. 页面级取数参数留在应用参数中，不放在这里。
    """

    run_id: int
    task_id: int
    adapter_key: str
    credentials: dict[str, Any]
    default_download_days: int
    start_date: str
    end_date: str
    trace_id: str
    extra: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def default_date_str() -> str:
        """默认业务日期：当天（YYYY-MM-DD）。"""
        return date.today().isoformat()

    @staticmethod
    def resolve_date_range(default_download_days: int) -> tuple[str, str]:
        """
        由“默认下载天数”换算日期范围。

        规则：
        1. end_date 固定为昨天；
        2. start_date = 昨天 - (days - 1)；
        3. days <= 0 时按 1 处理。
        """
        days = max(int(default_download_days or 1), 1)
        end_day = date.today() - timedelta(days=1)
        start_day = end_day - timedelta(days=days - 1)
        return start_day.isoformat(), end_day.isoformat()
