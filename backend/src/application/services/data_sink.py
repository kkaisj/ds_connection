"""
数据落地统一入口
用途：汇总“采集结果上传/入库”动作，避免各适配器重复实现上传逻辑。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


async def persist_rows(
    session: AsyncSession,
    storage_config_id: int,
    rows: list[dict],
    run_id: int,
) -> None:
    """
    统一的数据落地入口（MVP）。

    当前策略：
    - 先作为统一编排点，后续可在这里按 storage_config.type 分发到
      MySQL / 飞书多维表 / 钉钉表格 / 邮件等真实上传实现。
    - 目前不改变既有业务结果，只保证链路可扩展。
    """
    _ = session
    _ = storage_config_id
    _ = rows
    _ = run_id
    return None
