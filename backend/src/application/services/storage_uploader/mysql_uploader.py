"""
MySQL 上传器
用途：
1. 将统一数据对象写入 MySQL（当前唯一落地实现）。
2. 兼容“待插入字段”二维数组：第一行目标字段，第二行具体值/来源字段名。
"""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

from application.services.storage_uploader.base import BaseStorageUploader, DatasetPayload


def _normalize_table_name(dataset_name: str) -> str:
    """
    生成安全表名。
    若数据集名无法直接生成英文表名，则使用 hash 兜底。
    """
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", dataset_name or "").strip("_").lower()
    if not s:
        s = hashlib.md5((dataset_name or "dataset").encode("utf-8")).hexdigest()[:8]
    return f"rpa_{s}"


def _quote_ident(name: str) -> str:
    """MySQL 标识符转义。"""
    return f"`{name.replace('`', '')}`"


class MysqlStorageUploader(BaseStorageUploader):
    """MySQL 上传实现。"""

    storage_type = "mysql"

    def _read_source_rows(self, payload: DatasetPayload) -> list[dict[str, Any]]:
        """
        读取文件行数据。
        约定：
        1. 支持 csv/xlsx/xls。
        2. 若无文件则返回一条空行（仅用于常量写入模式）。
        """
        if not payload.exists_file:
            return [{}]

        file_path = payload.file_path.lower()
        try:
            import pandas as pd
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"缺少 pandas 依赖，无法读取文件: {e}") from e

        if file_path.endswith(".csv"):
            df = pd.read_csv(payload.file_path, dtype=str)
        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            df = pd.read_excel(payload.file_path, dtype=str)
        else:
            raise RuntimeError(f"暂不支持的文件类型: {payload.file_path}")

        df.fillna("", inplace=True)
        return df.to_dict(orient="records")

    def _build_target_rows(self, payload: DatasetPayload) -> list[dict[str, Any]]:
        """
        构建待写入行：
        1. `待插入字段` 第一行是目标字段。
        2. 第二行为值：若值命中源文件字段名，则取该列；否则按常量值写入。
        """
        target_fields = payload.target_fields
        source_values = payload.source_values
        if not target_fields:
            raise RuntimeError("待插入字段为空，无法写入")
        if len(target_fields) != len(source_values):
            raise RuntimeError("待插入字段二维数组长度不一致")

        source_rows = self._read_source_rows(payload)
        rows: list[dict[str, Any]] = []
        for source in source_rows:
            item: dict[str, Any] = {}
            for idx, target in enumerate(target_fields):
                source_or_value = source_values[idx]
                if source_or_value in source:
                    item[target] = source.get(source_or_value, "")
                else:
                    item[target] = source_or_value
            rows.append(item)
        return rows

    def upload(
        self,
        payload: DatasetPayload,
        storage_config: dict[str, Any],
        input_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        执行 MySQL upsert。
        storage_config 最小字段：
        - host / port / user / password / db_name
        可选字段：
        - table_name（默认根据数据集名自动生成）
        """
        _ = input_context
        host = str(storage_config.get("host") or storage_config.get("db_host") or "").strip()
        port = int(storage_config.get("port") or storage_config.get("db_port") or 3306)
        user = str(
            storage_config.get("user")
            or storage_config.get("db_user")
            or storage_config.get("username")
            or ""
        ).strip()
        password = str(storage_config.get("password") or storage_config.get("db_password") or "")
        db_name = str(
            storage_config.get("db_name")
            or storage_config.get("database")
            or storage_config.get("schema")
            or ""
        ).strip()
        table_name = str(storage_config.get("table_name") or "").strip() or _normalize_table_name(
            payload.dataset_name
        )

        if not host or not user or not db_name:
            raise RuntimeError("MySQL 配置不完整，至少需要 host/user/db_name")

        rows = self._build_target_rows(payload)
        if not rows:
            return {"storage_type": "mysql", "table_name": table_name, "rows_count": 0}

        all_fields = list(rows[0].keys())
        dedupe_keys = [k for k in payload.dedupe_keys if k in all_fields]
        if not dedupe_keys:
            dedupe_keys = [all_fields[0]]

        try:
            import pymysql  # noqa: F401
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"缺少 pymysql 依赖，无法写入 MySQL: {e}") from e

        engine = create_engine(
            f"mysql+pymysql://{user}:{quote_plus(password)}@{host}:{port}/{db_name}?charset=utf8mb4"
        )
        table_ident = _quote_ident(table_name)
        cols_sql = ", ".join(f"{_quote_ident(c)} TEXT NULL" for c in all_fields)
        pk_sql = ", ".join(_quote_ident(c) for c in dedupe_keys)
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_ident} (
            {cols_sql},
            PRIMARY KEY ({pk_sql})
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """

        cols = ", ".join(_quote_ident(c) for c in all_fields)
        values = ", ".join(f":{c}" for c in all_fields)
        updates = ", ".join(f"{_quote_ident(c)}=VALUES({_quote_ident(c)})" for c in all_fields)
        upsert_sql = text(f"INSERT INTO {table_ident} ({cols}) VALUES ({values}) ON DUPLICATE KEY UPDATE {updates}")

        with engine.begin() as conn:
            conn.execute(text(create_sql))
            conn.execute(upsert_sql, rows)

        return {
            "storage_type": "mysql",
            "table_name": table_name,
            "rows_count": len(rows),
            "dedupe_keys": dedupe_keys,
        }
