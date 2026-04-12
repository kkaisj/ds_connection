"""
文件归档处理器。
用途：
1. 在上传前后归档原文件与处理后文件，便于追溯。
2. 目录结构尽量贴合“平台/二级平台/店铺/日期”的业务习惯。
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def _safe_segment(value: str) -> str:
    """清理路径片段中的非法字符。"""
    text = (value or "").strip() or "unknown"
    for ch in [":", "\\", "/", "*", "?", '"', "<", ">", "|"]:
        text = text.replace(ch, "_")
    return text


class FileArchiveMover:
    """上传链路文件归档能力。"""

    def archive(
        self,
        *,
        source_file_path: str,
        root_dir: str,
        platform_name: str,
        sub_platform_name: str,
        shop_name: str,
        phase_name: str,
    ) -> str:
        """
        复制归档文件。
        说明：
        1. 使用 copy2 保留时间戳等元信息。
        2. 仅做归档复制，不删除源文件，降低误操作风险。
        """
        source = Path(source_file_path)
        if not source.exists():
            raise RuntimeError(f"待归档文件不存在: {source_file_path}")

        today = datetime.now().strftime("%Y-%m-%d")
        year = datetime.now().strftime("%Y")
        target_dir = (
            Path(root_dir)
            / _safe_segment(phase_name)
            / _safe_segment(platform_name)
            / _safe_segment(sub_platform_name)
            / _safe_segment(shop_name)
            / f"{year}年"
            / today
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        shutil.copy2(source, target)
        return str(target)

