"""
京东 - 退款数据同步适配器
使用 DrissionPage 采集京东退款记录。
"""

from typing import Any
from infrastructure.connectors.base.adapter import AdapterResult, BaseAdapter


class JdRefundSyncAdapter(BaseAdapter):
    adapter_key = "jd.refund_sync"

    async def execute(self, credentials: dict[str, Any], params: dict[str, Any] | None = None) -> AdapterResult:
        # TODO: 接入 DrissionPage 采集京东退款
        return AdapterResult(success=True, data=[], rows_count=0)

