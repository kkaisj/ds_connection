"""
文件预处理流水线。
用途：
1. 统一编排“批量插入字段 + 文件归档”。
2. 将文件处理结果回写为新的 file_path，供上传器继续使用。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from application.services.file_preprocess.append_columns_processor import AppendColumnsProcessor
from application.services.file_preprocess.file_archive_mover import FileArchiveMover
from application.services.storage_uploader.base import DatasetPayload


class FilePreprocessPipeline:
    """上传前文件预处理流水线。"""

    def __init__(self) -> None:
        self._append_processor = AppendColumnsProcessor()
        self._archive_mover = FileArchiveMover()

    def run(
        self,
        payload: DatasetPayload,
        *,
        input_context: dict[str, Any] | None = None,
    ) -> tuple[DatasetPayload, dict[str, Any]]:
        """
        执行预处理。
        input_context 约定字段（可选）：
        1. enable_append_columns: 是否执行批量插入字段（默认 true）
        2. archive_root_dir: 归档根目录；存在时自动归档
        3. platform_name/sub_platform_name/shop_name: 归档路径层级
        """
        ctx = input_context or {}
        outputs: dict[str, Any] = {
            "append_columns_file_path": None,
            "archive_original_file_path": None,
            "archive_processed_file_path": None,
        }
        current = payload

        if current.exists_file and bool(ctx.get("enable_append_columns", True)):
            processed_path = self._append_processor.process(
                file_path=current.file_path,
                target_fields=current.target_fields,
                source_values=current.source_values,
            )
            current = replace(current, file_path=processed_path)
            outputs["append_columns_file_path"] = processed_path

        archive_root = str(ctx.get("archive_root_dir") or "").strip()
        if archive_root and payload.exists_file:
            platform_name = str(ctx.get("platform_name") or "unknown")
            sub_platform_name = str(ctx.get("sub_platform_name") or "unknown")
            shop_name = str(ctx.get("shop_name") or "unknown")

            outputs["archive_original_file_path"] = self._archive_mover.archive(
                source_file_path=payload.file_path,
                root_dir=archive_root,
                platform_name=platform_name,
                sub_platform_name=sub_platform_name,
                shop_name=shop_name,
                phase_name="原文件",
            )
            if current.file_path and current.file_path != payload.file_path:
                outputs["archive_processed_file_path"] = self._archive_mover.archive(
                    source_file_path=current.file_path,
                    root_dir=archive_root,
                    platform_name=platform_name,
                    sub_platform_name=sub_platform_name,
                    shop_name=shop_name,
                    phase_name="处理后文件",
                )
        return current, outputs

