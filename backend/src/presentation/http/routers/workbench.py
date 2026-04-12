"""
统一开发工作台路由。
用途：
1. 提供规范中的 /api/v1/dev/workbench/* 入口。
2. 复用既有 dev/instructions 工作台能力，避免重复实现。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from presentation.http.routers import dev_instructions

router = APIRouter()


@router.post("/apps/create")
async def create_workbench_app(body: dev_instructions.ScaffoldCreateBody):
    """
    创建应用开发骨架。
    说明：
    1. 复用已有脚手架生成逻辑（登录/取数/适配器）。
    2. 作为规范中 `POST /api/v1/dev/workbench/apps/create` 的稳定入口。
    """
    return await dev_instructions.create_workbench_scaffold(body)


@router.put("/file")
async def save_workbench_file(body: dev_instructions.SaveInstructionBody):
    """
    保存工作台文件。
    说明：
    1. 复用已有内容保存逻辑。
    2. 作为规范中 `PUT /api/v1/dev/workbench/file` 的稳定入口。
    """
    return await dev_instructions.save_instruction_content(body)


@router.post("/fs/node")
async def create_workbench_node(body: dev_instructions.CreateNodeBody):
    """创建工作台目录或文件。"""
    return await dev_instructions.create_instruction_node(body)


@router.patch("/fs/node")
async def rename_workbench_node(body: dev_instructions.RenameNodeBody):
    """重命名工作台目录或文件。"""
    return await dev_instructions.rename_instruction_node(body)


@router.get("/fs/delete-check")
async def check_workbench_delete_node(
    relative_path: str,
    session: AsyncSession = Depends(get_db),  # noqa: B008
):
    """删除前检查工作台目录或文件。"""
    return await dev_instructions.check_delete_instruction_node(relative_path, session)


@router.delete("/fs/node")
async def delete_workbench_node(
    relative_path: str,
    session: AsyncSession = Depends(get_db),  # noqa: B008
):
    """删除工作台目录或文件。"""
    return await dev_instructions.delete_instruction_node(relative_path, session)


@router.post("/run")
async def run_workbench(body: dev_instructions.WorkbenchRunBody):
    """
    工作台测试运行。
    说明：
    1. 复用已有 workbench run 执行链路。
    2. 作为规范中 `POST /api/v1/dev/workbench/run` 的稳定入口。
    """
    return await dev_instructions.run_workbench_adapter(body)
