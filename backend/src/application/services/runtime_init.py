"""
应用运行初始化服务。
用途：
1. 任务执行或工作台试跑前，执行固定初始化动作。
2. 当前包含：清理 Downloads 文件夹、清理 WPS 进程。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def _safe_download_dir(path: str | None) -> Path:
    """解析下载目录，未传时默认用户 Downloads。"""
    if path and str(path).strip():
        return Path(path).expanduser().resolve()
    return (Path.home() / "Downloads").resolve()


def clean_download_dir(download_dir: str | None = None) -> dict[str, Any]:
    """
    清理下载目录中的文件和子目录。
    说明：
    1. 若目录不存在会自动创建。
    2. 返回删除数量与错误明细，便于日志记录。
    """
    target = _safe_download_dir(download_dir)
    target.mkdir(parents=True, exist_ok=True)

    removed_count = 0
    errors: list[str] = []
    for item in target.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink(missing_ok=True)
            else:
                shutil.rmtree(item, ignore_errors=False)
            removed_count += 1
        except Exception as e:  # pragma: no cover
            errors.append(f"{item.name}: {e}")

    return {"download_dir": str(target), "removed_count": removed_count, "errors": errors}


def kill_wps_processes(process_names: list[str] | None = None) -> dict[str, Any]:
    """
    清理 WPS 相关进程。
    默认目标：
    1. wps.exe
    2. wpscloudsvr.exe
    3. et.exe
    """
    targets = process_names or ["wps.exe", "wpscloudsvr.exe", "et.exe"]
    results: list[dict[str, Any]] = []

    for name in targets:
        cmd = ["taskkill", "/IM", name, "/F"]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
            returncode = completed.returncode
            stdout = (completed.stdout or "").strip()
            stderr = (completed.stderr or "").strip()
        except FileNotFoundError:
            returncode = 127
            stdout = ""
            stderr = "taskkill not found, skipped"
        results.append(
            {
                "process": name,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        )
    return {"killed": results}


def initialize_app_runtime(
    app_params: dict[str, Any] | None = None,
    *,
    force_clean_downloads: bool = True,
    force_kill_wps: bool = True,
) -> dict[str, Any]:
    """
    应用启动初始化统一入口。
    参数约定：
    1. app_params.download_dir: 下载目录（默认用户 Downloads）
    2. app_params.clean_downloads: 是否清理下载目录（默认 true）
    3. app_params.kill_wps_processes: 是否清理 WPS 进程（默认 true）
    """
    params = app_params or {}
    do_clean_downloads = bool(params.get("clean_downloads", True)) and force_clean_downloads
    do_kill_wps = bool(params.get("kill_wps_processes", True)) and force_kill_wps

    result: dict[str, Any] = {"clean_downloads": None, "kill_wps_processes": None}
    if do_clean_downloads:
        result["clean_downloads"] = clean_download_dir(str(params.get("download_dir") or ""))
    if do_kill_wps:
        result["kill_wps_processes"] = kill_wps_processes()
    return result

