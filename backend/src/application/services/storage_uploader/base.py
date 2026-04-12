"""
存储上传器基础模型与接口
用途：
1. 统一“中文业务数据对象”到“内部英文模型”的转换。
2. 约束不同存储介质上传器（mysql/feishu/dingtalk）的公共接口。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DatasetPayload:
    """
    内部统一数据对象（英文键）。
    说明：
    1. 对外仍兼容中文键（数据集/文件路径/待插入字段/去重主键）。
    2. `insert_fields_matrix` 约定为二维数组：
       第一行目标字段名，第二行对应值（常量值或来源字段名）。
    """

    dataset_name: str
    file_path: str
    insert_fields_matrix: list[list[str]]
    dedupe_keys: list[str]
    raw: dict[str, Any]

    @staticmethod
    def from_external(item: dict[str, Any]) -> "DatasetPayload":
        """将中文/英文混合键映射到统一内部模型。"""
        dataset_name = str(item.get("数据集") or item.get("dataset_name") or "").strip()
        file_path = str(item.get("文件路径") or item.get("file_path") or "").strip()
        matrix = item.get("待插入字段") or item.get("insert_fields_matrix") or []
        dedupe_keys = item.get("去重主键") or item.get("dedupe_keys") or []

        if not isinstance(matrix, list):
            matrix = []
        if not isinstance(dedupe_keys, list):
            dedupe_keys = []

        return DatasetPayload(
            dataset_name=dataset_name,
            file_path=file_path,
            insert_fields_matrix=matrix,
            dedupe_keys=[str(x) for x in dedupe_keys],
            raw=item,
        )

    @property
    def exists_file(self) -> bool:
        """文件路径是否存在。"""
        return bool(self.file_path) and Path(self.file_path).exists()

    @property
    def target_fields(self) -> list[str]:
        """目标字段名（待插入字段第一行）。"""
        if len(self.insert_fields_matrix) < 1:
            return []
        row = self.insert_fields_matrix[0]
        if not isinstance(row, list):
            return []
        return [str(x) for x in row]

    @property
    def source_values(self) -> list[str]:
        """对应值（待插入字段第二行）。"""
        if len(self.insert_fields_matrix) < 2:
            return []
        row = self.insert_fields_matrix[1]
        if not isinstance(row, list):
            return []
        return [str(x) for x in row]


class BaseStorageUploader:
    """上传器抽象基类。"""

    storage_type = "base"

    def upload(
        self,
        payload: DatasetPayload,
        storage_config: dict[str, Any],
        input_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """执行上传动作并返回结果摘要。"""
        raise NotImplementedError

