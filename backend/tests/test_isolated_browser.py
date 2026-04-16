"""
环境隔离浏览器管理器测试
验证会话复用与隔离策略，不依赖真实浏览器。
"""

import sys
import tempfile
import asyncio
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from infrastructure.connectors.base.isolated_browser import IsolatedBrowserManager


class _FakePage:
    def __init__(self) -> None:
        self.title = "ok"
        self.url = ""

    def get(self, url: str) -> None:
        self.url = url

    def quit(self) -> None:
        self.title = ""


def test_reuse_page_for_same_env() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = IsolatedBrowserManager(base_dir=Path(tmp), page_factory=lambda *_: _FakePage())
        p1 = manager.get_page(company="c1", platform="douyin", account="a1", start_url="https://a.com")
        p2 = manager.get_page(company="c1", platform="douyin", account="a1", start_url="https://b.com")
        assert p1 is p2
        assert p2.url == "https://b.com"


def test_isolated_page_for_different_account() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = IsolatedBrowserManager(base_dir=Path(tmp), page_factory=lambda *_: _FakePage())
        p1 = manager.get_page(company="c1", platform="douyin", account="a1")
        p2 = manager.get_page(company="c1", platform="douyin", account="a2")
        assert p1 is not p2


def test_dump_sessions_contains_profile_info() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = IsolatedBrowserManager(base_dir=Path(tmp), page_factory=lambda *_: _FakePage())
        _ = manager.get_page(company="c1", platform="taobao", account="shopA")
        dump = manager.dump_sessions()
        assert "taobao_shopA" in dump


def test_new_session_opens_default_entry_page_when_start_url_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manager = IsolatedBrowserManager(base_dir=Path(tmp), page_factory=lambda *_: _FakePage())
        page = manager.get_page(company="c1", platform="jd", account="a1")
        assert str(page.url).startswith("file:///") or page.url == "about:blank"


@pytest.mark.asyncio
async def test_get_page_in_asyncio_thread_uses_threadsafe_factory() -> None:
    """
    回归测试：
    在 asyncio 事件循环线程中请求页面时，页面工厂不能直接在当前线程执行。
    否则 Playwright Sync API 会报错 “inside the asyncio loop”。
    """

    class _ThreadCheckPage(_FakePage):
        pass

    def _factory(_: Path, __: str) -> _ThreadCheckPage:
        has_loop = True
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            has_loop = False
        if has_loop:
            raise RuntimeError("factory called in asyncio thread")
        return _ThreadCheckPage()

    with tempfile.TemporaryDirectory() as tmp:
        manager = IsolatedBrowserManager(base_dir=Path(tmp), page_factory=_factory)
        page = manager.get_page(company="c1", platform="jd", account="a_async")
        assert isinstance(page, _ThreadCheckPage)
