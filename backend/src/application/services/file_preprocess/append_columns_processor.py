"""
批量插入字段处理器。
用途：
1. 在上传前对单文件执行“批量插入字段”能力，产出处理后文件。
2. 兼容 csv/xlsx/xls，便于复用现有工具链的核心流程。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class AppendColumnsProcessor:
    """上传前的批量插入字段处理器。"""

    @staticmethod
    def _read_dataframe(file_path: str):
        """读取源文件为 DataFrame。"""
        try:
            import pandas as pd
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"缺少 pandas 依赖，无法执行批量插入字段: {e}") from e

        lower = file_path.lower()
        if lower.endswith(".csv"):
            return pd.read_csv(file_path, dtype=str)
        if lower.endswith(".xlsx") or lower.endswith(".xls"):
            return pd.read_excel(file_path, dtype=str)
        raise RuntimeError(f"不支持的文件类型: {file_path}")

    @staticmethod
    def _write_dataframe(df: Any, source_path: str) -> str:
        """
        写回处理后文件。
        约定：
        1. 统一产出 xlsx，命名为原文件名 + `_processed.xlsx`。
        2. 保留源文件，不在此处做删除，避免影响回溯与排错。
        """
        source = Path(source_path)
        target = source.with_name(f"{source.stem}_processed.xlsx")
        df.fillna("", inplace=True)
        df.to_excel(target, index=False)
        return str(target)

    def process(
        self,
        file_path: str,
        target_fields: list[str],
        source_values: list[str],
    ) -> str:
        """
        执行批量插入字段。
        规则：
        1. 仅对“常量值”字段执行追加。
        2. 若某 value 与源文件列名同名，则视为来源列映射，不做追加。
        """
        if not file_path:
            raise RuntimeError("文件路径为空，无法执行批量插入字段")
        if len(target_fields) != len(source_values):
            raise RuntimeError("待插入字段与对应值长度不一致")

        df = self._read_dataframe(file_path)
        existing = set(str(c) for c in df.columns)
        for idx, field in enumerate(target_fields):
            value = source_values[idx]
            if value in existing:
                continue
            df[field] = value
        return self._write_dataframe(df, file_path)

