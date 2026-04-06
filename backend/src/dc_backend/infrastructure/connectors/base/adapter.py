"""
适配器基类
所有 DrissionPage 浏览器自动化适配器必须继承此基类。
定义统一的生命周期方法：初始化 → 登录 → 采集 → 清理。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdapterResult:
    """
    适配器执行结果。
    success: 是否成功
    data: 采集到的数据列表
    error_code: 失败时的错误码
    error_message: 失败时的错误信息
    """
    success: bool = True
    data: list[dict[str, Any]] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    rows_count: int = 0


class BaseAdapter(ABC):
    """
    DrissionPage 浏览器自动化适配器基类。

    子类需实现：
    - execute(): 核心采集逻辑，接收账号凭据和任务参数，返回 AdapterResult

    生命周期：
    1. __init__() → 初始化适配器
    2. execute(credentials, params) → 执行采集（内部完成登录/导航/抓取/解析）
    3. cleanup() → 清理资源（关闭浏览器等）
    """

    # 适配器标识，与 connector_app.adapter_key 对应
    adapter_key: str = ""

    @abstractmethod
    async def execute(
        self,
        credentials: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> AdapterResult:
        """
        执行采集任务。

        Args:
            credentials: 账号凭据，包含 username / password / extra 等
            params: 任务自定义参数（来自 task_instance.params）

        Returns:
            AdapterResult 包含采集数据或错误信息
        """
        ...

    async def cleanup(self) -> None:
        """清理资源，子类可覆盖以关闭浏览器、释放连接等。"""
        pass
