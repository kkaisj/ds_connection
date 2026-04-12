"""
百度 demo 一键联调脚本
用途：快速验证“开发 -> 发版 -> 上架 -> 连接 -> 执行”最小链路。
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select


def _prepare_src_path() -> None:
    """确保脚本可直接以 `python -m scripts.run_baidu_demo` 方式运行。"""
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.append(str(src))


_prepare_src_path()

from application.services.task_executor import execute_task_run  # noqa: E402
from config.database import async_session_factory, engine  # noqa: E402
from infrastructure.persistence.models.models import (  # noqa: E402
    AdapterRelease,
    ConnectorApp,
    NotificationConfig,
    Platform,
    ShopAccount,
    StorageConfig,
    TaskInstance,
    TaskRun,
)


async def _ensure_platform(session) -> Platform:
    row = await session.scalar(
        select(Platform).where(Platform.code == "douyin", Platform.is_deleted.is_(False))
    )
    if row:
        return row
    platform = Platform(code="douyin", name="抖音", parent_id=None)
    session.add(platform)
    await session.commit()
    await session.refresh(platform)
    return platform


async def _ensure_release(session) -> AdapterRelease:
    release = await session.scalar(
        select(AdapterRelease).where(
            AdapterRelease.adapter_key == "demo.baidu_hello",
            AdapterRelease.version == "0.1.0",
            AdapterRelease.is_deleted.is_(False),
        )
    )
    if not release:
        release = AdapterRelease(adapter_key="demo.baidu_hello", version="0.1.0")
        session.add(release)
    release.status = "released"
    release.qa_passed = True
    release.checksum = "demo-baidu-hello-0.1.0"
    release.release_notes = "百度你好最小流程演示"
    release.released_by = "system-demo"
    release.released_at = datetime.now()
    await session.commit()
    await session.refresh(release)
    return release


async def _ensure_app(session, platform: Platform, release: AdapterRelease) -> ConnectorApp:
    app = await session.scalar(
        select(ConnectorApp).where(
            ConnectorApp.adapter_key == "demo.baidu_hello",
            ConnectorApp.is_deleted.is_(False),
        )
    )
    if app:
        app.status = "active"
        app.platform_id = platform.id
        app.version = "0.1.0"
        app.param_schema = {
            "is_published": True,
            "release_id": release.id,
            "release_checksum": release.checksum,
            "release_status": release.status,
        }
        await session.commit()
        await session.refresh(app)
        return app

    app = ConnectorApp(
        platform_id=platform.id,
        name="百度你好演示",
        adapter_key="demo.baidu_hello",
        version="0.1.0",
        status="active",
        description="最小自动化流程演示",
        param_schema={
            "is_published": True,
            "release_id": release.id,
            "release_checksum": release.checksum,
            "release_status": release.status,
        },
    )
    session.add(app)
    await session.commit()
    await session.refresh(app)
    return app


async def _ensure_account(session, platform: Platform) -> ShopAccount:
    account = await session.scalar(
        select(ShopAccount).where(
            ShopAccount.shop_name == "百度演示店铺",
            ShopAccount.is_deleted.is_(False),
        )
    )
    if account:
        return account
    account = ShopAccount(
        platform_id=platform.id,
        shop_name="百度演示店铺",
        username_enc=b"demo_user",
        password_enc=b"demo_password",
        extra_enc=b"{}",
        status="active",
        health_score=100,
        captcha_method="none",
        captcha_config=None,
        captcha_enabled=False,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


async def _ensure_storage(session) -> StorageConfig:
    storage = await session.scalar(
        select(StorageConfig).where(
            StorageConfig.name == "百度演示存储",
            StorageConfig.is_deleted.is_(False),
        )
    )
    if storage:
        return storage
    storage = StorageConfig(
        type="mysql",
        name="百度演示存储",
        config_enc=b"{}",
        status="active",
    )
    session.add(storage)
    await session.commit()
    await session.refresh(storage)
    return storage


async def _ensure_notification(session) -> NotificationConfig:
    cfg = await session.scalar(
        select(NotificationConfig).where(
            NotificationConfig.channel == "feishu",
            NotificationConfig.is_deleted.is_(False),
        )
    )
    if cfg:
        return cfg
    cfg = NotificationConfig(
        channel="feishu",
        webhook_url_enc=b"https://example.com/webhook",
        notify_on_fail=1,
        notify_on_retry_fail=1,
        notify_on_account_invalid=1,
        dedupe_window_sec=300,
        rate_limit_per_min=20,
        status="active",
    )
    session.add(cfg)
    await session.commit()
    await session.refresh(cfg)
    return cfg


async def _ensure_task(
    session,
    app: ConnectorApp,
    account: ShopAccount,
    storage: StorageConfig,
    notify: NotificationConfig,
) -> TaskInstance:
    task = await session.scalar(
        select(TaskInstance).where(
            TaskInstance.name == "百度你好演示任务",
            TaskInstance.is_deleted.is_(False),
        )
    )
    if task:
        task.status = "enabled"
        task.app_id = app.id
        task.account_id = account.id
        task.storage_config_id = storage.id
        task.notification_config_id = notify.id
        task.params = {"keyword": "你好", "real_browser": False}
        task.params["default_download_days"] = 1
        await session.commit()
        await session.refresh(task)
        return task

    task = TaskInstance(
        app_id=app.id,
        account_id=account.id,
        storage_config_id=storage.id,
        notification_config_id=notify.id,
        name="百度你好演示任务",
        cron_expr="*/5 * * * *",
        timezone="Asia/Shanghai",
        status="enabled",
        params={"keyword": "你好", "real_browser": False, "default_download_days": 1},
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def main() -> None:
    async with async_session_factory() as session:
        platform = await _ensure_platform(session)
        release = await _ensure_release(session)
        app = await _ensure_app(session, platform, release)
        account = await _ensure_account(session, platform)
        storage = await _ensure_storage(session)
        notify = await _ensure_notification(session)
        task = await _ensure_task(session, app, account, storage, notify)

        run = TaskRun(
            task_id=task.id,
            trigger_type="manual",
            status="pending",
            started_at=datetime.now(),
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

        await execute_task_run(session, run.id)
        latest = await session.get(TaskRun, run.id)

        print(
            f"[baidu-demo] task_id={task.id} run_id={run.id} "
            f"status={latest.status} error={latest.error_code or '-'}"
        )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
