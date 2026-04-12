"""
任务执行器
串联 "查任务配置 → 解密凭据 → 调用适配器 → 记录日志 → 更新状态" 的完整链路。
由调度器（APScheduler）或手动触发接口调用。
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.services.data_sink import persist_rows
from application.services.runtime_init import initialize_app_runtime
from infrastructure.connectors.base.execution_context import ExecutionContext
from infrastructure.connectors.base.registry import get_adapter
from infrastructure.persistence.models.models import (
    AdapterRelease,
    ConnectorApp,
    Platform,
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
    platform = await session.get(Platform, app.platform_id) if app else None

    if not app or not account:
        await _fail_run(session, run, "CONFIG_ERROR", "应用或账号配置不存在")
        return

    if not app.adapter_key:
        await _fail_run(session, run, "NO_ADAPTER", f"应用 {app.name} 未配置适配器")
        return

    # 运行前二次校验：只允许执行“已发版 + QA 通过”的适配器版本。
    release = await session.scalar(
        select(AdapterRelease).where(
            AdapterRelease.adapter_key == app.adapter_key,
            AdapterRelease.version == app.version,
            AdapterRelease.status == "released",
            AdapterRelease.qa_passed.is_(True),
            AdapterRelease.is_deleted.is_(False),
        )
    )
    if not release:
        await _fail_run(
            session,
            run,
            "RELEASE_NOT_READY",
            f"适配器 {app.adapter_key}@{app.version} 未发版或未通过 QA",
        )
        return

    # ── 2. 更新状态为 running ──
    run.status = "running"
    run.started_at = datetime.now()
    await session.commit()

    # 运行前初始化：清理 Downloads + 清理 WPS 进程。
    runtime_init_result = initialize_app_runtime(task.params or {})

    await _add_log(
        session,
        run.id,
        "start",
        "INFO",
        f"开始执行: {task.name} (适配器: {app.adapter_key})",
        ext={
            "adapter_key": app.adapter_key,
            "adapter_version": app.version,
            "release_id": release.id,
            "release_checksum": release.checksum,
            "runtime_init": runtime_init_result,
        },
    )

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
    app_params = task.params or {}
    default_days_raw = app_params.get("default_download_days", 1)
    try:
        default_download_days = max(int(default_days_raw), 1)
    except (TypeError, ValueError):
        default_download_days = 1

    # 优先使用默认下载天数换算范围；兼容旧参数（start_date/end_date）作为兜底。
    start_date, end_date = ExecutionContext.resolve_date_range(default_download_days)
    if app_params.get("start_date") and app_params.get("end_date"):
        start_date = str(app_params.get("start_date"))
        end_date = str(app_params.get("end_date"))

    execution_context = ExecutionContext(
        run_id=run.id,
        task_id=task.id,
        adapter_key=app.adapter_key,
        credentials=credentials,
        default_download_days=default_download_days,
        start_date=start_date,
        end_date=end_date,
        trace_id=f"run-{run.id}",
        extra={
            # 浏览器隔离上下文：后续适配器通过 get_web_page() 自动读取，不再硬编码。
            "company_name": str(app_params.get("company_name") or "dc_connection"),
            "platform_code": str(
                (platform.code if platform else "") or app.adapter_key.split(".")[0]
            ),
            "account_name": str(app_params.get("account_name") or account.shop_name or account.id),
            "browser_zoom": str(app_params.get("browser_zoom") or "75"),
        },
    )

    try:
        await _add_log(session, run.id, "adapter_exec", "INFO", "适配器开始采集")
        if hasattr(adapter, "execute_with_context"):
            result = await adapter.execute_with_context(execution_context, app_params)  # type: ignore[attr-defined]
        else:
            # 兼容旧适配器：仍允许走历史 execute(credentials, params) 入口。
            result = await adapter.execute(credentials, app_params)
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
        # 统一数据落地点：适配器只负责取数，上传/入库在应用层统一处理。
        sink_result = await persist_rows(
            session=session,
            storage_config_id=task.storage_config_id,
            rows=result.data,
            run_id=run.id,
            input_context={
                "adapter_key": app.adapter_key,
                "dataset_name": app.name,
                "platform_name": platform.name if platform else "",
                "sub_platform_name": platform.name if platform else "",
                "shop_name": account.shop_name,
                "archive_root_dir": str(app_params.get("archive_root_dir") or ""),
                "enable_append_columns": bool(app_params.get("enable_append_columns", True)),
            },
        )
        run.status = "success"
        run.ended_at = now
        run.duration_ms = duration_ms
        await _add_log(
            session,
            run.id,
            "complete",
            "INFO",
            f"采集完成，共 {result.rows_count} 条数据",
            ext={"sink_result": sink_result},
        )
    else:
        run.status = "failed"
        run.ended_at = now
        run.duration_ms = duration_ms
        run.error_code = result.error_code
        run.error_message = result.error_message
        await _add_log(
            session,
            run.id,
            "failed",
            "ERROR",
            f"{result.error_code}: {result.error_message}",
        )

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


async def _add_log(
    session: AsyncSession,
    run_id: int,
    step: str,
    level: str,
    message: str,
    ext: dict | None = None,
) -> None:
    """写入步骤日志。"""
    log = TaskRunLog(run_id=run_id, step=step, level=level, message=message, ext=ext)
    session.add(log)
    await session.flush()

