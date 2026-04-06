"""
任务执行器
串联 "查任务配置 → 解密凭据 → 调用适配器 → 记录日志 → 更新状态" 的完整链路。
由调度器（APScheduler）或手动触发接口调用。
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dc_backend.infrastructure.connectors.base.registry import get_adapter
from dc_backend.infrastructure.persistence.models.models import (
    ConnectorApp,
    ShopAccount,
    TaskInstance,
    TaskRun,
    TaskRunLog,
)

logger = logging.getLogger(__name__)


async def execute_task_run(session: AsyncSession, run_id: int) -> None:
    """
    执行一次任务运行。

    流程：
    1. 查询 TaskRun → TaskInstance → ConnectorApp → ShopAccount
    2. 将 TaskRun 状态更新为 running
    3. 根据 ConnectorApp.adapter_key 获取 DrissionPage 适配器
    4. 调用适配器的 execute() 方法
    5. 根据结果更新 TaskRun 状态为 success / failed
    6. 记录步骤日志到 task_run_log
    """
    # ── 1. 加载运行记录和关联数据 ──
    run = await session.get(TaskRun, run_id)
    if not run:
        logger.error(f"TaskRun {run_id} 不存在")
        return

    task = await session.get(TaskInstance, run.task_id)
    if not task:
        logger.error(f"TaskInstance {run.task_id} 不存在")
        return

    app = await session.get(ConnectorApp, task.app_id)
    account = await session.get(ShopAccount, task.account_id)

    if not app or not account:
        await _fail_run(session, run, "CONFIG_ERROR", "应用或账号配置不存在")
        return

    if not app.adapter_key:
        await _fail_run(session, run, "NO_ADAPTER", f"应用 {app.name} 未配置适配器")
        return

    # ── 2. 更新状态为 running ──
    run.status = "running"
    run.started_at = datetime.now()
    await session.commit()

    await _add_log(session, run.id, "start", "INFO", f"开始执行: {task.name} (适配器: {app.adapter_key})")

    # ── 3. 获取适配器 ──
    try:
        adapter = get_adapter(app.adapter_key)
    except (ValueError, ImportError) as e:
        await _fail_run(session, run, "ADAPTER_NOT_FOUND", str(e))
        return

    # ── 4. 构造凭据并执行 ──
    credentials = {
        "username": account.username_enc.decode("utf-8", errors="replace"),
        "password": account.password_enc.decode("utf-8", errors="replace"),
        "extra": account.extra_enc.decode("utf-8", errors="replace") if account.extra_enc else None,
    }

    try:
        await _add_log(session, run.id, "adapter_exec", "INFO", "适配器开始采集")
        result = await adapter.execute(credentials, task.params)
    except Exception as e:
        logger.exception(f"适配器执行异常: {app.adapter_key}")
        await _fail_run(session, run, "ADAPTER_EXCEPTION", str(e))
        return
    finally:
        # 无论成功失败都要清理资源
        try:
            await adapter.cleanup()
        except Exception:
            logger.warning("适配器清理资源异常", exc_info=True)

    # ── 5. 根据结果更新状态 ──
    now = datetime.now()
    duration_ms = int((now - run.started_at).total_seconds() * 1000) if run.started_at else 0

    if result.success:
        run.status = "success"
        run.ended_at = now
        run.duration_ms = duration_ms
        await _add_log(session, run.id, "complete", "INFO", f"采集完成，共 {result.rows_count} 条数据")
    else:
        run.status = "failed"
        run.ended_at = now
        run.duration_ms = duration_ms
        run.error_code = result.error_code
        run.error_message = result.error_message
        await _add_log(session, run.id, "failed", "ERROR", f"{result.error_code}: {result.error_message}")

    # 更新任务实例的最后执行时间
    task.last_run_at = now
    await session.commit()

    logger.info(f"TaskRun {run_id} 执行完成: {run.status} ({duration_ms}ms)")


async def _fail_run(session: AsyncSession, run: TaskRun, code: str, msg: str) -> None:
    """将运行记录标记为失败。"""
    run.status = "failed"
    run.ended_at = datetime.now()
    run.error_code = code
    run.error_message = msg
    if run.started_at:
        run.duration_ms = int((run.ended_at - run.started_at).total_seconds() * 1000)
    await _add_log(session, run.id, "error", "ERROR", f"{code}: {msg}")
    await session.commit()
    logger.error(f"TaskRun {run.id} 失败: {code} - {msg}")


async def _add_log(session: AsyncSession, run_id: int, step: str, level: str, message: str) -> None:
    """写入步骤日志。"""
    log = TaskRunLog(run_id=run_id, step=step, level=level, message=message)
    session.add(log)
    await session.flush()
