"""
环境隔离浏览器管理器
用途：为每个“平台 + 账号”复用独立 Chrome Profile，并返回可复用的网页对象。
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass
class BrowserSession:
    """已打开浏览器会话信息。"""

    page: Any
    company_dir: Path
    profile_name: str
    last_access_at: datetime


def _sanitize_name(value: str) -> str:
    """清理路径不安全字符，复用环境隔离目录命名规则。"""
    s = (value or "").strip() or "unknown"
    for ch in [":", "\\", "/", "*", "?", '"', "<", ">", "|", " "]:
        s = s.replace(ch, "_")
    return s


def _touch_preferences(profile_dir: Path, zoom: str = "75") -> None:
    """
    创建 profile 时兜底初始化 Preferences，避免首次启动没有配置文件导致异常。
    然后复用 chrome/init_chrome.py 中的偏好写入逻辑。
    """
    profile_dir.mkdir(parents=True, exist_ok=True)
    pref_path = profile_dir / "Preferences"
    if not pref_path.exists():
        pref_path.write_text("{}", encoding="utf-8")
    _set_profile_exit_type(profile_dir, zoom=zoom)


def _set_profile_exit_type(profile_dir: Path, zoom: str = "75") -> None:
    """
    按 chrome/init_chrome.py 的思路写入关键配置（无 xbot 依赖版）。
    """
    zoom_level = {
        "50": -3.8017840169239308,
        "75": -1.5778829311823859,
        "100": 0.0,
    }.get(str(zoom), 0.0)

    pref_path = profile_dir / "Preferences"
    try:
        raw = pref_path.read_text(encoding="utf-8")
        data = json.loads(raw or "{}")
    except Exception:
        data = {}

    default_save_dir = str(Path(os.path.expanduser("~")) / "Downloads")
    data["download"] = {
        "prompt_for_download": False,
        "default_directory": default_save_dir,
    }
    data["savefile"] = {"default_directory": default_save_dir}
    data["download_bubble"] = {"partial_view_enabled": False, "partial_view_impressions": 6}
    data.setdefault("partition", {})
    data["partition"]["default_zoom_level"] = {"x": zoom_level}
    data["partition"]["per_host_zoom_levels"] = {"x": {}}
    data.setdefault("profile", {})
    data["profile"]["exit_type"] = "Normal"
    data["profile"]["default_content_setting_values"] = {"popups": 1}
    data["credentials_enable_autosignin"] = False
    data["credentials_enable_service"] = False
    data["password_manager"] = {
        "autofillable_credentials_account_store_login_database": False,
        "autofillable_credentials_profile_store_login_database": False,
    }

    pref_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _default_page_factory(company_dir: Path, profile_name: str):
    """
    默认页面工厂：使用 DrissionPage 打开独立 profile。
    """
    from DrissionPage import ChromiumOptions, ChromiumPage

    co = ChromiumOptions()
    co.set_user_data_path(str(company_dir))
    co.set_argument(f'--profile-directory={profile_name}')
    co.set_argument("--disable-popup-blocking")
    co.set_argument("--no-first-run")
    co.set_argument("--disable-signin-screen")
    return ChromiumPage(addr_or_opts=co)


def _resolve_default_entry_url() -> str:
    """
    解析隔离浏览器默认启动页。
    优先使用仓库内 `chrome/start.html`，找不到时回退到 `about:blank`。
    """
    repo_root = Path(__file__).resolve().parents[5]
    candidates = [
        repo_root / "tools" / "chrome" / "start.html",
        repo_root / "chrome" / "start.html",
    ]
    for start_html in candidates:
        if start_html.exists():
            return start_html.as_uri()
    return "about:blank"


class IsolatedBrowserManager:
    """
    环境隔离浏览器管理器。

    约定：
    1. 每个 (company, platform, account) 对应唯一独立 profile。
    2. 同一 profile 复用已打开 page 对象，后续应用直接获取即可。
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        page_factory: Callable[[Path, str], Any] | None = None,
    ) -> None:
        home = Path(os.path.expanduser("~"))
        self._base_dir = base_dir or (home / "CHROME" / "USER_DATA")
        self._page_factory = page_factory or _default_page_factory
        self._sessions: dict[str, BrowserSession] = {}
        self._lock = Lock()

    def _session_key(self, company: str, platform: str, account: str) -> str:
        return f"{_sanitize_name(company)}::{_sanitize_name(platform)}::{_sanitize_name(account)}"

    def _profile_paths(self, company: str, platform: str, account: str) -> tuple[Path, str, Path]:
        company_name = _sanitize_name(company)
        profile_name = f"{_sanitize_name(platform)}_{_sanitize_name(account)}"
        company_dir = self._base_dir / company_name
        profile_dir = company_dir / profile_name
        return company_dir, profile_name, profile_dir

    @staticmethod
    def _is_page_alive(page: Any) -> bool:
        """最小化探测 page 是否可复用。"""
        try:
            _ = page.title
            return True
        except Exception:
            return False

    def get_page(
        self,
        *,
        company: str,
        platform: str,
        account: str,
        start_url: str | None = None,
        zoom: str = "75",
    ):
        """
        获取可复用的隔离 page。
        如果会话已存在且存活，直接复用；否则新建并缓存。
        """
        key = self._session_key(company, platform, account)
        company_dir, profile_name, profile_dir = self._profile_paths(company, platform, account)

        with self._lock:
            cached = self._sessions.get(key)
            if cached and self._is_page_alive(cached.page):
                if start_url:
                    cached.page.get(start_url)
                cached.last_access_at = datetime.now()
                return cached.page

            _touch_preferences(profile_dir, zoom=zoom)
            page = self._page_factory(company_dir, profile_name)
            page.get(start_url or _resolve_default_entry_url())
            self._sessions[key] = BrowserSession(
                page=page,
                company_dir=company_dir,
                profile_name=profile_name,
                last_access_at=datetime.now(),
            )
            return page

    def close_page(self, *, company: str, platform: str, account: str) -> None:
        """关闭指定隔离会话。"""
        key = self._session_key(company, platform, account)
        with self._lock:
            session = self._sessions.pop(key, None)
        if session:
            try:
                session.page.quit()
            except Exception:
                pass

    def close_all(self) -> None:
        """关闭全部隔离会话。"""
        with self._lock:
            items = list(self._sessions.values())
            self._sessions.clear()
        for session in items:
            try:
                session.page.quit()
            except Exception:
                pass

    def dump_sessions(self) -> str:
        """返回会话快照（用于调试）。"""
        with self._lock:
            data = {
                key: {
                    "company_dir": str(value.company_dir),
                    "profile_name": value.profile_name,
                    "last_access_at": value.last_access_at.isoformat(timespec="seconds"),
                }
                for key, value in self._sessions.items()
            }
        return json.dumps(data, ensure_ascii=False, indent=2)


_MANAGER = IsolatedBrowserManager()


def get_isolated_page(
    *,
    company: str,
    platform: str,
    account: str,
    start_url: str | None = None,
    zoom: str = "75",
):
    """模块级便捷函数：获取环境隔离 page。"""
    return _MANAGER.get_page(
        company=company,
        platform=platform,
        account=account,
        start_url=start_url,
        zoom=zoom,
    )
