"""
数据落地统一入口。
用途：
1. 汇总“取数结果 -> 文件预处理 -> 按存储介质上传”的完整链路。
2. 屏蔽适配器差异，统一兼容中文数据集对象与普通行数据。
"""

from __future__ import annotations

import ast
import asyncio
import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from application.services.file_preprocess.pipeline import FilePreprocessPipeline
from application.services.storage_uploader.base import DatasetPayload
from application.services.storage_uploader.factory import create_storage_uploader
from infrastructure.persistence.models.models import StorageConfig


def _decode_storage_config(config_enc: bytes) -> dict[str, Any]:
    """
    解析存储配置。
    说明：
    1. 兼容标准 JSON 字符串。
    2. 兼容历史 `str(dict)` 文本格式。
    """
    raw = (config_enc or b"").decode("utf-8", errors="replace").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        pass
    try:
        obj = ast.literal_eval(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _is_dataset_payload_row(item: dict[str, Any]) -> bool:
    """判断行对象是否为“数据集对象”格式。"""
    keys = set(item.keys())
    return bool({"数据集", "dataset_name"} & keys and {"待插入字段", "insert_fields_matrix"} & keys)


def _materialize_plain_rows(
    rows: list[dict[str, Any]],
    *,
    input_context: dict[str, Any] | None = None,
) -> tuple[DatasetPayload | None, str | None]:
    """
    将普通行记录转换为标准数据集对象。
    返回：
    1. DatasetPayload（若无可用数据则为 None）
    2. 临时文件路径（用于后续清理）
    """
    if not rows:
        return None, None

    columns = list(rows[0].keys())
    for row in rows[1:]:
        for key in row.keys():
            if key not in columns:
                columns.append(key)
    if not columns:
        return None, None

    fd, temp_path = tempfile.mkstemp(prefix="dc_plain_rows_", suffix=".csv")
    os.close(fd)
    Path(temp_path).unlink(missing_ok=True)
    with Path(temp_path).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in columns})

    context = input_context or {}
    dataset_name = str(context.get("dataset_name") or context.get("adapter_key") or "默认数据集")
    dedupe_keys = context.get("dedupe_keys") or [columns[0]]
    payload = DatasetPayload(
        dataset_name=dataset_name,
        file_path=temp_path,
        insert_fields_matrix=[columns, columns],
        dedupe_keys=[str(k) for k in dedupe_keys],
        raw={"source": "plain_rows", "rows_count": len(rows)},
    )
    return payload, temp_path


async def persist_rows(
    session: AsyncSession,
    storage_config_id: int,
    rows: list[dict],
    run_id: int,
    *,
    input_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    执行统一数据落地流程。
    流程：
    1. 加载并解析存储配置。
    2. 规范化采集结果。
    3. 执行文件预处理（插入字段 + 归档）。
    4. 按存储类型分发上传。
    """
    if not rows:
        return {"run_id": run_id, "uploaded_count": 0, "items": []}

    storage = await session.get(StorageConfig, storage_config_id)
    if not storage or storage.is_deleted or storage.status != "active":
        raise RuntimeError(f"存储配置不可用: id={storage_config_id}")

    storage_config = _decode_storage_config(storage.config_enc)
    uploader = create_storage_uploader(storage.type)
    preprocess = FilePreprocessPipeline()

    payloads: list[DatasetPayload] = []
    temp_files: list[str] = []
    if _is_dataset_payload_row(rows[0]):
        payloads = [DatasetPayload.from_external(item) for item in rows]
    else:
        payload, temp_file = _materialize_plain_rows(rows, input_context=input_context)
        if payload:
            payloads = [payload]
        if temp_file:
            temp_files.append(temp_file)

    context = dict(input_context or {})
    context.setdefault("run_id", run_id)
    context.setdefault("storage_config_id", storage_config_id)
    context.setdefault("storage_type", storage.type)

    outputs: list[dict[str, Any]] = []
    try:
        for payload in payloads:
            current_payload, preprocess_meta = preprocess.run(payload, input_context=context)
            upload_meta = await asyncio.to_thread(
                uploader.upload,
                current_payload,
                storage_config,
                context,
            )
            outputs.append(
                {
                    "dataset_name": current_payload.dataset_name,
                    "file_path": current_payload.file_path,
                    "preprocess": preprocess_meta,
                    "upload": upload_meta,
                }
            )
    finally:
        for path in temp_files:
            Path(path).unlink(missing_ok=True)

    return {"run_id": run_id, "uploaded_count": len(outputs), "items": outputs}
