"""
网页取数适配器模板基类
用途：将“登录”和“取数”拆成固定钩子，便于各平台页面自动化扩展复用。
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from infrastructure.connectors.base.adapter import AdapterResult, BaseAdapter
from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.base.isolated_browser import get_isolated_page


class BaseWebDataAdapter(BaseAdapter):
    """
    面向“页面取数”场景的统一模板。

    执行顺序：
    1. create_context：构建执行上下文（浏览器会话、trace 信息等）
    2. ensure_login：统一登录入口（可按平台实现）
    3. collect_rows：仅关注取数逻辑（分页、字段提取、清洗）
    4. cleanup：资源回收（由 BaseAdapter 生命周期统一触发）
    """

    async def execute(
        self,
        credentials: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> AdapterResult:
        """
        模板方法：固定编排登录与取数流程。
        子类只需要覆盖 create_context / ensure_login / collect_rows。
        """
        app_params = params or {}
        execution_context = self._build_context_from_legacy(credentials, app_params)
        context = await self.create_context(execution_context, app_params)
        await self.ensure_login(context, execution_context, app_params)
        rows = await self.collect_rows(context, execution_context, app_params)
        return AdapterResult(success=True, rows_count=len(rows), data=rows)

    async def execute_with_context(
        self,
        execution_context: ExecutionContext,
        app_params: dict[str, Any] | None = None,
    ) -> AdapterResult:
        """
        新执行入口：直接使用全局 ExecutionContext + 应用参数。
        """
        params = app_params or {}
        context = await self.create_context(execution_context, params)
        await self.ensure_login(context, execution_context, params)
        rows = await self.collect_rows(context, execution_context, params)
        return AdapterResult(success=True, rows_count=len(rows), data=rows)

    async def create_context(
        self,
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> dict[str, Any]:
        """构建执行上下文，默认返回空字典，子类可按需扩展。"""
        _ = execution_context
        _ = app_params
        return {}

    async def ensure_login(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> None:
        """
        统一登录入口，默认 no-op。
        需要登录的平台在子类中覆盖。
        """
        _ = context
        _ = execution_context
        _ = app_params
        return None

    @abstractmethod
    async def collect_rows(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """子类仅实现取数逻辑，返回标准化行数据列表。"""
        ...

    def _build_context_from_legacy(
        self,
        credentials: dict[str, Any],
        app_params: dict[str, Any],
    ) -> ExecutionContext:
        """
        兼容旧调用方式时，兜底构建执行上下文。
        """
        default_days_raw = app_params.get("default_download_days", 1)
        try:
            default_download_days = max(int(default_days_raw), 1)
        except (TypeError, ValueError):
            default_download_days = 1
        start_date, end_date = ExecutionContext.resolve_date_range(default_download_days)
        if app_params.get("start_date") and app_params.get("end_date"):
            start_date = str(app_params.get("start_date"))
            end_date = str(app_params.get("end_date"))
        return ExecutionContext(
            run_id=0,
            task_id=0,
            adapter_key=self.adapter_key,
            credentials=credentials,
            default_download_days=default_download_days,
            start_date=start_date,
            end_date=end_date,
            trace_id=f"legacy-{self.adapter_key}",
        )

    def get_web_page(
        self,
        execution_context: ExecutionContext,
        *,
        start_url: str | None = None,
        app_params: dict[str, Any] | None = None,
        company: str | None = None,
        platform: str | None = None,
        account: str | None = None,
        zoom: str | None = None,
    ):
        """
        获取环境隔离网页对象（可复用）。
        后续应用可直接调用该方法，无需重复编写浏览器初始化逻辑。
        """
        # 统一从“显式参数 -> 应用参数 -> 全局上下文 -> 默认值”分层解析浏览器隔离标识。
        # 这样应用侧只需传业务参数，不需要重复关心 profile 目录规则。
        params = app_params or {}
        extra = execution_context.extra or {}
        resolved_company = str(
            company
            or params.get("company_name")
            or extra.get("company_name")
            or "dc_connection"
        )
        resolved_platform = str(
            platform
            or params.get("platform_code")
            or extra.get("platform_code")
            or self.adapter_key.split(".")[0]
        )
        resolved_account = str(
            account
            or params.get("account_name")
            or extra.get("account_name")
            or execution_context.credentials.get("username")
            or execution_context.task_id
            or "default"
        )
        resolved_zoom = str(
            zoom
            or params.get("browser_zoom")
            or extra.get("browser_zoom")
            or "75"
        )
        return get_isolated_page(
            company=resolved_company,
            platform=resolved_platform,
            account=resolved_account,
            start_url=start_url,
            zoom=resolved_zoom,
        )
