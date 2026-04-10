"""
基础冒烟测试：确保应用入口可初始化，并注册核心路由。
"""

from pathlib import Path
import sys


sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from main import create_app


def test_create_app_registers_core_routes() -> None:
    app = create_app()
    route_paths = {route.path for route in app.routes}
    assert "/api/v1/apps" in route_paths
    assert "/api/v1/tasks" in route_paths
    assert any(path.startswith("/api/v1/dashboard") for path in route_paths)
