"""
适配器注册表
通过 adapter_key 查找并实例化对应的 DrissionPage 适配器。
新增平台适配器时，只需在 _REGISTRY 中注册即可。
"""

from dc_backend.infrastructure.connectors.base.adapter import BaseAdapter


# 适配器注册表：adapter_key → 适配器类的导入路径
# 使用延迟导入避免启动时加载所有适配器模块
_REGISTRY: dict[str, str] = {
    "taobao.order_sync": "dc_backend.infrastructure.connectors.taobao.order_sync.TaobaoOrderSyncAdapter",
    "taobao.logistics_track": "dc_backend.infrastructure.connectors.taobao.logistics_track.TaobaoLogisticsTrackAdapter",
    "jd.product_stock_sync": "dc_backend.infrastructure.connectors.jd.product_stock_sync.JdProductStockSyncAdapter",
    "jd.refund_sync": "dc_backend.infrastructure.connectors.jd.refund_sync.JdRefundSyncAdapter",
    "pdd.review_scrape": "dc_backend.infrastructure.connectors.pdd.review_scrape.PddReviewScrapeAdapter",
    "douyin.traffic_analytics": "dc_backend.infrastructure.connectors.douyin.traffic_analytics.DouyinTrafficAnalyticsAdapter",
}


def get_adapter(adapter_key: str) -> BaseAdapter:
    """
    根据 adapter_key 获取适配器实例。
    使用延迟导入，仅在需要时加载对应模块。

    Raises:
        ValueError: adapter_key 未注册
        ImportError: 适配器模块不存在
    """
    class_path = _REGISTRY.get(adapter_key)
    if not class_path:
        raise ValueError(f"未注册的适配器: {adapter_key}")

    # 延迟导入：拆分模块路径和类名
    module_path, class_name = class_path.rsplit(".", 1)

    import importlib
    module = importlib.import_module(module_path)
    adapter_cls = getattr(module, class_name)
    return adapter_cls()


def list_registered_adapters() -> list[str]:
    """返回所有已注册的适配器 key 列表。"""
    return list(_REGISTRY.keys())
