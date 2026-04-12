"""
连接器注册表
通过 adapter_key 查找并实例化对应的 DrissionPage 连接器实现。

说明：
- 对外提供“可上架应用模板”元数据（中文名称、描述、默认版本）
- 对内保留 adapter_key 和类路径映射，用于实际执行
"""

from infrastructure.connectors.base.adapter import BaseAdapter

# 连接器注册表：adapter_key -> 元数据
# class_path 为运行时导入路径；display_name/description/default_version 用于上架页面展示
_REGISTRY: dict[str, dict[str, str]] = {
    "demo.baidu_hello": {
        "class_path": "infrastructure.connectors.demo.baidu_hello.DemoBaiduHelloAdapter",
        "platform_code": "douyin",
        "display_name": "百度你好演示",
        "description": "演示自动化：打开百度，输入“你好”，点击搜索",
        "default_version": "0.1.0",
    },
}


def get_adapter(adapter_key: str) -> BaseAdapter:
    """
    根据 adapter_key 获取适配器实例。
    使用延迟导入，仅在需要时加载对应模块。

    Raises:
        ValueError: adapter_key 未注册
        ImportError: 适配器模块不存在
    """
    meta = _REGISTRY.get(adapter_key)
    if not meta:
        raise ValueError(f"未注册的适配器: {adapter_key}")

    class_path = meta["class_path"]

    module_path, class_name = class_path.rsplit(".", 1)

    import importlib

    module = importlib.import_module(module_path)
    adapter_cls = getattr(module, class_name)
    return adapter_cls()


def list_registered_adapters() -> list[str]:
    """返回所有已注册的适配器 key 列表。"""
    return list(_REGISTRY.keys())


def get_adapter_meta(adapter_key: str) -> dict[str, str] | None:
    """返回指定适配器元数据，不存在则返回 None。"""
    return _REGISTRY.get(adapter_key)


def list_registered_adapter_templates() -> list[dict[str, str]]:
    """
    返回可用于上架页面的应用模板列表。
    每个模板包含中文应用名、平台、描述、默认版本和 adapter_key。
    """
    items: list[dict[str, str]] = []
    for adapter_key, meta in _REGISTRY.items():
        items.append(
            {
                "adapter_key": adapter_key,
                "platform_code": meta["platform_code"],
                "display_name": meta["display_name"],
                "description": meta["description"],
                "default_version": meta["default_version"],
            }
        )
    return items
