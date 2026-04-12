"""
飞书多维表格上传器骨架。
用途：
1. 预留飞书多维表格上传入口，保证 data_sink 路由完整。
2. 在未接入真实飞书 SDK 前，返回结构化占位结果，便于前后端联调。
"""

from __future__ import annotations

from typing import Any

from application.services.storage_uploader.base import BaseStorageUploader, DatasetPayload


class FeishuBitableStorageUploader(BaseStorageUploader):
    """飞书多维表格上传器（骨架）。"""

    storage_type = "feishu_bitable"

    def upload(
        self,
        payload: DatasetPayload,
        storage_config: dict[str, Any],
        input_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        骨架行为：
        1. 不抛错中断主链路，返回 `pending_implementation` 状态。
        2. 回传最小上下文，便于 UI 与日志验证路由是否正确。
        """
        _ = storage_config
        _ = input_context
        return {
            "storage_type": self.storage_type,
            "status": "pending_implementation",
            "dataset_name": payload.dataset_name,
            "rows_count": 0,
            "message": "飞书多维表格上传器骨架已就位，待接入真实 API。",
        }

