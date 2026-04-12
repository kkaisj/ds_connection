"""
存储上传器工厂。
用途：
1. 按 storage_type 统一创建上传器实例，避免上层直接依赖具体实现。
2. 当前先支持 mysql，后续可平滑扩展 feishu_bitable / dingtalk_sheet。
"""

from __future__ import annotations

from application.services.storage_uploader.base import BaseStorageUploader
from application.services.storage_uploader.dingtalk_sheet_uploader import (
    DingtalkSheetStorageUploader,
)
from application.services.storage_uploader.feishu_bitable_uploader import (
    FeishuBitableStorageUploader,
)
from application.services.storage_uploader.mysql_uploader import MysqlStorageUploader


def create_storage_uploader(storage_type: str) -> BaseStorageUploader:
    """
    按存储类型返回上传器实例。
    说明：
    1. storage_type 大小写不敏感，内部统一转小写处理。
    2. 暂不支持的类型会抛出明确异常，避免静默失败。
    """
    key = (storage_type or "").strip().lower()
    if key == "mysql":
        return MysqlStorageUploader()
    if key == "feishu_bitable":
        return FeishuBitableStorageUploader()
    if key == "dingtalk_sheet":
        return DingtalkSheetStorageUploader()
    raise RuntimeError(f"未知存储类型: {key}")
