"""
开发指令工作台路由
用途：
1. 提供“我开发的指令”列表与代码读取能力。
2. 提供工作台代码保存、应用三件套（登录/取数/适配器）脚手架生成能力。
3. 提供工作台调试运行能力，支持按“适配器编排”直接试跑。
"""

from __future__ import annotations

import importlib
import inspect
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.services.runtime_init import initialize_app_runtime
from config.database import get_db
from infrastructure.connectors.base.adapter import BaseAdapter
from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.base.registry import get_adapter, get_adapter_meta
from infrastructure.persistence.models.models import AdapterRelease, ConnectorApp, TaskInstance

router = APIRouter()


class SaveInstructionBody(BaseModel):
    """保存工作台代码请求体。"""

    relative_path: str = Field(..., description="connectors 根目录下相对路径，仅允许 .py")
    content: str = Field(..., description="完整代码内容")


class ScaffoldCreateBody(BaseModel):
    """生成“登录 + 取数 + 适配器编排”三件套脚手架请求体。"""

    platform_code: str = Field(..., description="一级平台标识，如 douyin/pdd/taobao")
    app_slug: str = Field(..., description="应用标识，如 product_overview")
    target_dir: str | None = Field(None, description="可选：指定创建目录（connectors 相对路径）")
    overwrite: bool = Field(False, description="是否覆盖已有文件")


class WorkbenchRunBody(BaseModel):
    """工作台测试运行请求体。"""

    adapter_key: str | None = Field(None, description="已注册适配器 key")
    relative_path: str | None = Field(None, description="适配器相对路径（未注册草稿可用）")
    credentials: dict[str, Any] = Field(default_factory=dict, description="测试账号凭据")
    app_params: dict[str, Any] = Field(default_factory=dict, description="应用参数")
    extra: dict[str, Any] = Field(default_factory=dict, description="执行上下文扩展参数")


class CreateNodeBody(BaseModel):
    """工作台创建目录/文件请求体。"""

    relative_path: str = Field(..., description="connectors 根目录下相对路径")
    is_dir: bool = Field(False, description="是否创建目录，false 为创建 .py 文件")
    content: str = Field("", description="创建文件时的初始内容")


class RenameNodeBody(BaseModel):
    """工作台重命名目录/文件请求体。"""

    old_relative_path: str = Field(..., description="原相对路径")
    new_relative_path: str = Field(..., description="新相对路径")


def _connectors_root() -> Path:
    """定位 connectors 根目录。"""
    return Path(__file__).resolve().parents[3] / "infrastructure" / "connectors"


def _ensure_python_file_path(relative_path: str) -> Path:
    """
    校验并返回安全的 .py 文件路径。
    安全约束：
    1. 只能在 connectors 目录下。
    2. 只允许 .py 文件。
    3. 拒绝路径穿越。
    """
    root = _connectors_root().resolve()
    normalized = relative_path.strip().replace("\\", "/")
    target = (root / normalized).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("非法路径")
    if target.suffix != ".py":
        raise ValueError("仅支持 .py 文件")
    return target


def _ensure_connector_path(relative_path: str) -> Path:
    """
    校验并返回 connectors 下任意节点路径（目录或 .py 文件）。
    """
    root = _connectors_root().resolve()
    normalized = relative_path.strip().replace("\\", "/").strip("/")
    if not normalized:
        raise ValueError("路径不能为空")
    target = (root / normalized).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("非法路径")
    if target.exists() and target.is_file() and target.suffix != ".py":
        raise ValueError("仅支持 .py 文件")
    if not target.exists() and Path(normalized).suffix and Path(normalized).suffix != ".py":
        raise ValueError("仅支持 .py 文件")
    return target


def _ensure_not_base_path(target: Path) -> None:
    """
    防止误操作 connectors/base 目录。
    """
    root = _connectors_root().resolve()
    rel = target.resolve().relative_to(root).as_posix()
    if rel == "base" or rel.startswith("base/"):
        raise ValueError("不允许修改 base 目录")


def _to_relative_path(target: Path) -> str:
    """将绝对路径转换为 connectors 相对路径。"""
    return target.resolve().relative_to(_connectors_root().resolve()).as_posix()


def _adapter_key_from_special_file(relative_path: str) -> str | None:
    """
    从 login/collect/schema/tests 文件路径推断 adapter_key。
    """
    normalized = relative_path.strip().replace("\\", "/").strip("/")
    parts = normalized.split("/")
    if len(parts) < 3:
        return None
    group = parts[0]
    if group not in {"login", "collect_data", "schema", "tests"}:
        return None
    name = parts[-1]
    module_dir = "/".join(parts[1:-1]).replace("/", ".")
    if not module_dir:
        return None

    if group == "login" and name.endswith("_login.py"):
        return f"{module_dir}.{name[:-9]}"
    if group == "collect_data" and name.endswith("_collect.py"):
        return f"{module_dir}.{name[:-11]}"
    if group == "schema" and name.endswith("_schema.py"):
        return f"{module_dir}.{name[:-10]}"
    if group == "tests" and name.startswith("test_") and name.endswith(".py"):
        return f"{module_dir}.{name[5:-3]}"
    return None


def _collect_related_adapter_keys(target: Path) -> set[str]:
    """
    为目录/文件收集关联的 adapter_key，用于删除前安全检查。
    """
    root = _connectors_root().resolve()
    paths: list[Path] = []
    if target.is_dir():
        paths = [item for item in target.rglob("*.py") if item.is_file()]
    elif target.is_file():
        paths = [target]

    keys: set[str] = set()
    for file in paths:
        rel = file.resolve().relative_to(root).as_posix()
        direct = _file_to_adapter_key(file, root)
        if direct:
            keys.add(direct)
            continue
        inferred = _adapter_key_from_special_file(rel)
        if inferred:
            keys.add(inferred)
    return keys


def _list_dev_files(root: Path) -> list[Path]:
    """
    扫描可展示的开发文件。
    规则：
    1. 仅扫描 .py 文件。
    2. 跳过 __init__.py、__pycache__ 与 base 目录。
    """
    files: list[Path] = []
    for file in root.rglob("*.py"):
        parts = set(file.parts)
        if "__pycache__" in parts:
            continue
        if file.name == "__init__.py":
            continue
        if "base" in parts:
            continue
        files.append(file)
    return files


def _list_dev_dirs(root: Path) -> list[Path]:
    """
    扫描可展示的开发目录（包含空目录）。
    规则：
    1. 跳过 __pycache__ 与 base 目录。
    2. 不返回 connectors 根目录本身。
    """
    dirs: list[Path] = []
    for item in root.rglob("*"):
        if not item.is_dir():
            continue
        parts = set(item.parts)
        if "__pycache__" in parts:
            continue
        if "base" in parts:
            continue
        if item.resolve() == root.resolve():
            continue
        dirs.append(item)
    return dirs


def _infer_kind(path: Path, connectors_root: Path) -> str:
    """根据路径推断代码类型。"""
    rel = path.relative_to(connectors_root).as_posix()
    if rel.startswith("login/"):
        return "login_instruction"
    if rel.startswith("collect_data/"):
        return "collect_instruction"
    return "adapter"


def _file_to_adapter_key(path: Path, connectors_root: Path) -> str | None:
    """
    将适配器文件路径映射为 adapter_key。
    示例：demo/baidu_hello.py -> demo.baidu_hello
    """
    rel = path.relative_to(connectors_root)
    if len(rel.parts) < 2:
        return None
    if rel.parts[0] in ("login", "collect_data", "base"):
        return None
    return f"{rel.parts[0]}.{path.stem}"


def _to_pascal(value: str) -> str:
    """下划线命名转换为 PascalCase。"""
    cleaned = value.replace("-", "_")
    return "".join(part.capitalize() for part in cleaned.split("_") if part)


def _ensure_package_init_files(target_file: Path, root: Path) -> None:
    """
    递归补全 __init__.py，确保新建模块可被 import。
    """
    current = target_file.parent
    while str(current).startswith(str(root)) and current != root.parent:
        init_file = current / "__init__.py"
        if not init_file.exists():
            init_file.write_text("", encoding="utf-8")
        if current == root:
            break
        current = current.parent


def _build_scaffold_content(platform_code: str, app_slug: str, target_dir: str | None = None) -> dict[str, str]:
    """
    生成应用三件套模板内容。
    包含：
    1. 登录指令文件。
    2. 取数指令文件。
    3. 应用适配器编排文件（登录 + 取数）。
    """
    pascal = _to_pascal(app_slug)
    login_cls = f"{pascal}LoginInstruction"
    collect_cls = f"{pascal}CollectInstruction"
    adapter_cls = f"{pascal}Adapter"
    adapter_key = f"{platform_code}.{app_slug}"

    scaffold_dir = (target_dir or platform_code).strip().replace("\\", "/").strip("/")
    module_dir = scaffold_dir.replace("/", ".")
    login_path = f"login/{scaffold_dir}/{app_slug}_login.py"
    collect_path = f"collect_data/{scaffold_dir}/{app_slug}_collect.py"
    adapter_path = f"{scaffold_dir}/{app_slug}.py"

    login_code = f'''"""
登录指令：{platform_code}/{app_slug}
用途：
1. 封装平台登录动作，供多个取数应用复用。
2. 当前为骨架实现，后续按页面元素补齐具体登录步骤。
"""

from __future__ import annotations

from typing import Any

from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.login.base_login_instruction import BaseLoginInstruction


class {login_cls}(BaseLoginInstruction):
    """平台登录指令骨架。"""

    async def run(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> None:
        """
        登录逻辑入口。
        说明：
        1. 可通过 context["page_getter"] 获取隔离浏览器页面对象。
        2. 可通过 execution_context.credentials 读取账号密码。
        """
        _ = context
        _ = execution_context
        _ = app_params
        return None
'''

    collect_code = f'''"""
取数指令：{platform_code}/{app_slug}
用途：
1. 聚焦页面取数动作，不处理登录和上传逻辑。
2. 按统一返回格式输出行数据，交由应用层统一上传。
"""

from __future__ import annotations

from typing import Any

from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.collect_data.base_collect_instruction import BaseCollectInstruction


class {collect_cls}(BaseCollectInstruction):
    """页面取数指令骨架。"""

    async def run(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        取数逻辑入口。
        说明：
        1. 可通过 context["page_getter"] 获取隔离浏览器页面对象并操作页面。
        2. 建议使用 execution_context.start_date/end_date 作为日期范围。
        """
        _ = context
        _ = execution_context
        _ = app_params
        return []
'''

    adapter_code = f'''"""
应用适配器：{platform_code}/{app_slug}
用途：
1. 作为“登录 + 取数 + 上传”链路中的编排层。
2. 登录和取数逻辑分别复用指令集，适配器只负责参数组织和调用。
"""

from __future__ import annotations

from typing import Any

from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.base.web_data_adapter import BaseWebDataAdapter
from infrastructure.connectors.collect_data.{module_dir}.{app_slug}_collect import {collect_cls}
from infrastructure.connectors.login.{module_dir}.{app_slug}_login import {login_cls}


class {adapter_cls}(BaseWebDataAdapter):
    """应用适配器编排骨架。"""

    adapter_key = "{adapter_key}"

    def __init__(self) -> None:
        super().__init__()
        self._login_instruction = {login_cls}()
        self._collect_instruction = {collect_cls}()

    async def create_context(
        self,
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        构建运行上下文。
        说明：
        1. 统一暴露 page_getter，供登录/取数指令复用隔离浏览器。
        2. 可在此注入业务参数，如店铺、报表维度等。
        """
        def page_getter(start_url: str):
            return self.get_web_page(
                execution_context,
                start_url=start_url,
                app_params=app_params,
            )

        return {{
            "page_getter": page_getter,
            "start_date": execution_context.start_date,
            "end_date": execution_context.end_date,
        }}

    async def ensure_login(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> None:
        """调用登录指令。"""
        await self._login_instruction.run(context, execution_context, app_params)

    async def collect_rows(
        self,
        context: dict[str, Any],
        execution_context: ExecutionContext,
        app_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """调用取数指令并返回标准化行数据。"""
        return await self._collect_instruction.run(context, execution_context, app_params)
'''

    return {
        login_path: login_code,
        collect_path: collect_code,
        adapter_path: adapter_code,
    }


def _load_adapter_from_path(relative_path: str) -> BaseAdapter:
    """
    按相对路径动态加载适配器实例。
    约束：
    1. relative_path 必须是 connectors 下的 .py。
    2. 仅加载该模块内声明的 BaseAdapter 子类。
    """
    target = _ensure_python_file_path(relative_path)
    root = _connectors_root().resolve()
    rel_no_suffix = target.relative_to(root).as_posix().removesuffix(".py")
    module_name = f"infrastructure.connectors.{rel_no_suffix.replace('/', '.')}"

    module = importlib.import_module(module_name)
    module = importlib.reload(module)
    candidates: list[type[BaseAdapter]] = []
    for _, obj in module.__dict__.items():
        if not inspect.isclass(obj):
            continue
        if not issubclass(obj, BaseAdapter) or obj is BaseAdapter:
            continue
        if obj.__module__ != module.__name__:
            continue
        candidates.append(obj)

    if not candidates:
        raise ValueError("目标文件中未找到适配器类（BaseAdapter 子类）")
    return candidates[0]()


@router.get("")
async def list_dev_instructions(
    keyword: str | None = Query(None, description="按名称/路径搜索"),
    session: AsyncSession = Depends(get_db),  # noqa: B008
):
    """
    查询“我开发的指令/适配器”列表。
    返回字段包含：名称、类型、更新时间、状态、相对路径。
    """
    root = _connectors_root()
    files = _list_dev_files(root)
    dirs = _list_dev_dirs(root)

    release_rows = await session.execute(
        select(AdapterRelease).where(AdapterRelease.is_deleted.is_(False))
    )
    release_map: dict[str, AdapterRelease] = {}
    for row in release_rows.scalars().all():
        key = row.adapter_key
        existing = release_map.get(key)
        if not existing:
            release_map[key] = row
            continue
        existing_time = existing.released_at or existing.updated_at or datetime.min
        current_time = row.released_at or row.updated_at or datetime.min
        if current_time > existing_time:
            release_map[key] = row

    items: list[dict[str, Any]] = []
    for dir_path in dirs:
        rel_path = dir_path.relative_to(root).as_posix()
        name = dir_path.name
        updated_at = datetime.fromtimestamp(dir_path.stat().st_mtime).isoformat(timespec="seconds")
        item = {
            "name": name,
            "kind": "folder",
            "status": "目录",
            "updated_at": updated_at,
            "relative_path": rel_path,
            "adapter_key": None,
            "is_dir": True,
        }
        if keyword:
            kw = keyword.strip().lower()
            text = f"{name} {rel_path}".lower()
            if kw not in text:
                continue
        items.append(item)

    for file in files:
        rel_path = file.relative_to(root).as_posix()
        name = file.stem
        kind = _infer_kind(file, root)
        updated_at = datetime.fromtimestamp(file.stat().st_mtime).isoformat(timespec="seconds")

        status = "编辑中"
        adapter_key = _file_to_adapter_key(file, root)
        if adapter_key:
            release = release_map.get(adapter_key)
            if release and release.status == "released" and release.qa_passed:
                status = "已发版"
            elif get_adapter_meta(adapter_key):
                status = "已注册"

        item = {
            "name": name,
            "kind": kind,
            "status": status,
            "updated_at": updated_at,
            "relative_path": rel_path,
            "adapter_key": adapter_key,
            "is_dir": False,
        }
        if keyword:
            kw = keyword.strip().lower()
            text = f"{name} {rel_path} {status}".lower()
            if kw not in text:
                continue
        items.append(item)

    items.sort(key=lambda x: x["updated_at"], reverse=True)
    return {"code": 0, "message": "ok", "data": items}


@router.get("/content")
async def get_instruction_content(
    relative_path: str = Query(..., description="相对 connectors 路径"),
):
    """读取指定代码文件内容。"""
    try:
        target = _ensure_python_file_path(relative_path)
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}
    if not target.exists():
        return {"code": 404, "message": "文件不存在", "data": None}

    content = target.read_text(encoding="utf-8")
    updated_at = datetime.fromtimestamp(target.stat().st_mtime).isoformat(timespec="seconds")
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "relative_path": relative_path,
            "content": content,
            "updated_at": updated_at,
        },
    }


@router.put("/content")
async def save_instruction_content(body: SaveInstructionBody):
    """
    保存工作台代码内容。
    说明：
    1. 新文件不存在时会自动创建目录和文件。
    2. 会自动补齐目录 __init__.py，保证可 import。
    """
    try:
        target = _ensure_python_file_path(body.relative_path)
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}

    root = _connectors_root().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    _ensure_package_init_files(target, root)
    target.write_text(body.content, encoding="utf-8")

    updated_at = datetime.fromtimestamp(target.stat().st_mtime).isoformat(timespec="seconds")
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "relative_path": body.relative_path,
            "updated_at": updated_at,
        },
    }


@router.post("/fs/node")
async def create_instruction_node(body: CreateNodeBody):
    """
    创建目录或 .py 文件。
    """
    try:
        target = _ensure_connector_path(body.relative_path)
        _ensure_not_base_path(target)
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}

    if target.exists():
        return {"code": 409, "message": "目标已存在", "data": None}

    if body.is_dir:
        target.mkdir(parents=True, exist_ok=True)
        init_file = target / "__init__.py"
        if not init_file.exists():
            init_file.write_text("", encoding="utf-8")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        _ensure_package_init_files(target, _connectors_root().resolve())
        target.write_text(body.content or "", encoding="utf-8")

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "relative_path": _to_relative_path(target),
            "is_dir": bool(body.is_dir),
        },
    }


@router.patch("/fs/node")
async def rename_instruction_node(body: RenameNodeBody):
    """
    重命名目录或 .py 文件。
    """
    try:
        old_target = _ensure_connector_path(body.old_relative_path)
        new_target = _ensure_connector_path(body.new_relative_path)
        _ensure_not_base_path(old_target)
        _ensure_not_base_path(new_target)
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}

    if not old_target.exists():
        return {"code": 404, "message": "原路径不存在", "data": None}
    if new_target.exists():
        return {"code": 409, "message": "目标路径已存在", "data": None}

    if old_target.is_file() and old_target.suffix != ".py":
        return {"code": 400, "message": "仅支持 .py 文件", "data": None}
    if new_target.suffix and new_target.suffix != ".py":
        return {"code": 400, "message": "仅支持 .py 文件", "data": None}

    new_target.parent.mkdir(parents=True, exist_ok=True)
    old_target.rename(new_target)
    if new_target.is_file():
        _ensure_package_init_files(new_target, _connectors_root().resolve())

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "old_relative_path": _to_relative_path(old_target),
            "new_relative_path": _to_relative_path(new_target),
        },
    }


@router.get("/fs/delete-check")
async def check_delete_instruction_node(
    relative_path: str = Query(..., description="connectors 相对路径"),
    session: AsyncSession = Depends(get_db),  # noqa: B008
):
    """
    删除前检查：是否已发版、已上架或已被连接任务使用。
    """
    try:
        target = _ensure_connector_path(relative_path)
        _ensure_not_base_path(target)
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}

    if not target.exists():
        return {"code": 404, "message": "目标不存在", "data": None}

    adapter_keys = sorted(_collect_related_adapter_keys(target))
    if not adapter_keys:
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "can_delete": True,
                "adapter_keys": [],
                "released_count": 0,
                "listed_count": 0,
                "task_count": 0,
            },
        }

    release_rows = await session.execute(
        select(AdapterRelease).where(
            AdapterRelease.adapter_key.in_(adapter_keys),
            AdapterRelease.is_deleted.is_(False),
            AdapterRelease.status == "released",
            AdapterRelease.qa_passed.is_(True),
        )
    )
    listed_rows = await session.execute(
        select(ConnectorApp).where(
            ConnectorApp.adapter_key.in_(adapter_keys),
            ConnectorApp.is_deleted.is_(False),
            ConnectorApp.status == "active",
        )
    )
    task_rows = await session.execute(
        select(TaskInstance).join(ConnectorApp, TaskInstance.app_id == ConnectorApp.id).where(
            ConnectorApp.adapter_key.in_(adapter_keys),
            ConnectorApp.is_deleted.is_(False),
            TaskInstance.is_deleted.is_(False),
        )
    )

    released_count = len(release_rows.scalars().all())
    listed_count = len(listed_rows.scalars().all())
    task_count = len(task_rows.scalars().all())
    can_delete = released_count == 0 and listed_count == 0 and task_count == 0

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "can_delete": can_delete,
            "adapter_keys": adapter_keys,
            "released_count": released_count,
            "listed_count": listed_count,
            "task_count": task_count,
        },
    }


@router.delete("/fs/node")
async def delete_instruction_node(
    relative_path: str = Query(..., description="connectors 相对路径"),
    session: AsyncSession = Depends(get_db),  # noqa: B008
):
    """
    删除目录或 .py 文件。
    """
    try:
        target = _ensure_connector_path(relative_path)
        _ensure_not_base_path(target)
    except ValueError as e:
        return {"code": 400, "message": str(e), "data": None}

    if not target.exists():
        return {"code": 404, "message": "目标不存在", "data": None}

    adapter_keys = sorted(_collect_related_adapter_keys(target))
    if adapter_keys:
        release_rows = await session.execute(
            select(AdapterRelease).where(
                AdapterRelease.adapter_key.in_(adapter_keys),
                AdapterRelease.is_deleted.is_(False),
                AdapterRelease.status == "released",
                AdapterRelease.qa_passed.is_(True),
            )
        )
        listed_rows = await session.execute(
            select(ConnectorApp).where(
                ConnectorApp.adapter_key.in_(adapter_keys),
                ConnectorApp.is_deleted.is_(False),
                ConnectorApp.status == "active",
            )
        )
        task_rows = await session.execute(
            select(TaskInstance).join(ConnectorApp, TaskInstance.app_id == ConnectorApp.id).where(
                ConnectorApp.adapter_key.in_(adapter_keys),
                ConnectorApp.is_deleted.is_(False),
                TaskInstance.is_deleted.is_(False),
            )
        )
        if release_rows.scalars().first() or listed_rows.scalars().first() or task_rows.scalars().first():
            return {"code": 409, "message": "目标已发版/上架/被连接任务使用，禁止删除", "data": None}

    if target.is_dir():
        shutil.rmtree(target)
    else:
        if target.suffix != ".py":
            return {"code": 400, "message": "仅支持 .py 文件", "data": None}
        target.unlink(missing_ok=True)

    return {"code": 0, "message": "ok", "data": {"relative_path": relative_path}}


@router.post("/workbench/scaffold")
async def create_workbench_scaffold(body: ScaffoldCreateBody):
    """
    生成应用三件套脚手架：
    1. 登录指令。
    2. 取数指令。
    3. 应用适配器编排。
    """
    platform = body.platform_code.strip().lower()
    app_slug = body.app_slug.strip().lower().replace("-", "_")
    target_dir = (body.target_dir or "").strip().lower().replace("\\", "/").strip("/")
    if target_dir and (".." in target_dir or target_dir.startswith("/")):
        return {"code": 400, "message": "target_dir 非法", "data": None}
    if not platform or not app_slug:
        return {"code": 400, "message": "platform_code 和 app_slug 不能为空", "data": None}

    root = _connectors_root().resolve()
    files = _build_scaffold_content(platform, app_slug, target_dir or None)

    results: list[dict[str, Any]] = []
    for relative_path, content in files.items():
        target = _ensure_python_file_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        _ensure_package_init_files(target, root)
        exists = target.exists()
        if exists and not body.overwrite:
            results.append(
                {
                    "relative_path": relative_path,
                    "created": False,
                    "message": "已存在，已跳过",
                }
            )
            continue
        target.write_text(content, encoding="utf-8")
        results.append(
            {
                "relative_path": relative_path,
                "created": True,
                "message": "已生成",
            }
        )

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "platform_code": platform,
            "app_slug": app_slug,
            "target_dir": target_dir or platform,
            "files": results,
            "adapter_key": f"{platform}.{app_slug}",
        },
    }


@router.post("/workbench/run")
async def run_workbench_adapter(body: WorkbenchRunBody):
    """
    工作台调试运行。
    调试入口支持：
    1. adapter_key（已注册适配器）。
    2. relative_path（草稿适配器文件）。
    """
    if not body.adapter_key and not body.relative_path:
        return {"code": 400, "message": "adapter_key 或 relative_path 至少提供一个", "data": None}

    app_params = dict(body.app_params or {})
    raw_input = app_params.get("input") if isinstance(app_params.get("input"), dict) else {}
    unified_input: dict[str, Any] = dict(raw_input or {})
    page_params = dict(unified_input.get("page_params") or {})
    storage = dict(unified_input.get("storage") or app_params.get("storage") or {})
    runtime = dict(unified_input.get("runtime") or {})
    account_config = dict(unified_input.get("account_config") or {})
    credentials = dict(unified_input.get("credentials") or body.credentials or {})

    default_days_raw = unified_input.get("default_download_days", app_params.get("default_download_days", 1))
    try:
        default_download_days = max(int(default_days_raw), 1)
    except (TypeError, ValueError):
        default_download_days = 1

    runtime.setdefault("real_browser", bool(app_params.get("real_browser", True)))
    unified_input = {
        "credentials": credentials,
        "page_params": page_params,
        "account_config": account_config,
        "default_download_days": default_download_days,
        "runtime": runtime,
        "storage": storage,
    }
    app_params["input"] = unified_input
    app_params.setdefault("storage", storage)
    app_params.setdefault("page_params", page_params)
    app_params["default_download_days"] = default_download_days
    app_params["real_browser"] = bool(runtime.get("real_browser", True))
    app_params.setdefault("workbench_collect_only", True)

    start_date, end_date = ExecutionContext.resolve_date_range(default_download_days)
    if app_params.get("start_date") and app_params.get("end_date"):
        start_date = str(app_params.get("start_date"))
        end_date = str(app_params.get("end_date"))

    adapter_key = body.adapter_key or ""
    if not adapter_key and body.relative_path:
        adapter_key = body.relative_path.replace("\\", "/").removesuffix(".py").replace("/", ".")

    execution_context = ExecutionContext(
        run_id=0,
        task_id=0,
        adapter_key=adapter_key,
        credentials=credentials,
        default_download_days=default_download_days,
        start_date=start_date,
        end_date=end_date,
        trace_id=f"workbench-{int(time.time())}",
        extra=body.extra or {},
    )

    start_ts = time.time()
    logs: list[dict[str, Any]] = []
    logs.append({"time": datetime.now().isoformat(timespec="seconds"), "message": "开始执行"})
    runtime_init = initialize_app_runtime(app_params)
    logs.append(
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "message": "运行前初始化完成（清理 Downloads + 清理 WPS 进程）",
            "ext": runtime_init,
        }
    )

    try:
        if body.adapter_key:
            adapter = get_adapter(body.adapter_key)
            logs.append(
                {
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "message": f"通过注册表加载适配器: {body.adapter_key}",
                }
            )
        else:
            assert body.relative_path is not None
            adapter = _load_adapter_from_path(body.relative_path)
            logs.append(
                {
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "message": f"通过路径加载草稿适配器: {body.relative_path}",
                }
            )
    except Exception as e:
        return {"code": 400, "message": f"适配器加载失败: {e}", "data": None}

    try:
        if hasattr(adapter, "execute_with_context"):
            result = await adapter.execute_with_context(execution_context, app_params)  # type: ignore[attr-defined]
        else:
            result = await adapter.execute(credentials, app_params)
        cost_ms = int((time.time() - start_ts) * 1000)
        logs.append(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "message": f"执行完成，耗时 {cost_ms}ms",
            }
        )
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "success": bool(result.success),
                "rows_count": int(result.rows_count),
                "error_code": result.error_code,
                "error_message": result.error_message,
                "duration_ms": cost_ms,
                "logs": logs,
                "data_preview": (result.data or [])[:20],
                "start_date": start_date,
                "end_date": end_date,
                "default_download_days": default_download_days,
                "runtime_init": runtime_init,
            },
        }
    except Exception as e:
        cost_ms = int((time.time() - start_ts) * 1000)
        logs.append(
            {
                "time": datetime.now().isoformat(timespec="seconds"),
                "message": f"执行失败: {e}",
            }
        )
        return {
            "code": 500,
            "message": "运行失败",
            "data": {
                "success": False,
                "error_message": str(e),
                "duration_ms": cost_ms,
                "logs": logs,
                "data_preview": [],
                "start_date": start_date,
                "end_date": end_date,
                "default_download_days": default_download_days,
                "runtime_init": runtime_init,
            },
        }
    finally:
        try:
            await adapter.cleanup()
        except Exception:
            pass
