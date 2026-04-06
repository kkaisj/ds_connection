"""
淘宝天猫 - 物流轨迹更新适配器
使用 DrissionPage 采集物流轨迹信息。
"""

from typing import Any
from dc_backend.infrastructure.connectors.base.adapter import AdapterResult, BaseAdapter


class TaobaoLogisticsTrackAdapter(BaseAdapter):
    adapter_key = "taobao.logistics_track"

    async def execute(self, credentials: dict[str, Any], params: dict[str, Any] | None = None) -> AdapterResult:
        # TODO: 接入 DrissionPage 采集物流轨迹
        return AdapterResult(success=True, data=[], rows_count=0)
