"""
拼多多 - 评价数据抓取适配器
使用 DrissionPage 采集拼多多商品评价。
"""

from typing import Any
from infrastructure.connectors.base.adapter import AdapterResult, BaseAdapter


class PddReviewScrapeAdapter(BaseAdapter):
    adapter_key = "pdd.review_scrape"

    async def execute(self, credentials: dict[str, Any], params: dict[str, Any] | None = None) -> AdapterResult:
        # TODO: 接入 DrissionPage 采集拼多多评价
        return AdapterResult(success=True, data=[], rows_count=0)

