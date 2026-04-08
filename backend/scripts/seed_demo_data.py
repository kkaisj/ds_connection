# 数据库种子数据脚本
# 用法: cd backend && python -m scripts.seed_demo_data

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from config.database import async_session_factory, engine, Base
from infrastructure.persistence.models.models import (
    Platform,
    ConnectorApp,
    ShopAccount,
    StorageConfig,
    NotificationConfig,
    TaskInstance,
    TaskRun,
)
from datetime import datetime, timedelta
import random


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # 检查是否已有数据
        from sqlalchemy import select, func

        count = await session.scalar(select(func.count()).select_from(Platform))
        if count and count > 0:
            print("数据库已有数据，跳过种子。")
            return

        # ── 平台 ──
        platforms = [
            Platform(code="taobao", name="淘宝天猫"),
            Platform(code="jd", name="京东"),
            Platform(code="pdd", name="拼多多"),
            Platform(code="douyin", name="抖音"),
        ]
        session.add_all(platforms)
        await session.flush()

        # ── 连接应用 ──
        apps = [
            ConnectorApp(platform_id=platforms[0].id, name="订单数据采集", version="1.0.0", description="采集淘宝天猫订单数据"),
            ConnectorApp(platform_id=platforms[0].id, name="物流轨迹更新", version="1.0.0", description="更新淘宝天猫物流信息"),
            ConnectorApp(platform_id=platforms[1].id, name="商品库存同步", version="1.0.0", description="同步京东商品库存"),
            ConnectorApp(platform_id=platforms[1].id, name="退款数据同步", version="1.0.0", description="同步京东退款记录"),
            ConnectorApp(platform_id=platforms[2].id, name="评价数据抓取", version="1.0.0", description="抓取拼多多评价数据"),
            ConnectorApp(platform_id=platforms[3].id, name="流量数据采集", version="1.0.0", description="采集抖音流量数据"),
        ]
        session.add_all(apps)
        await session.flush()

        # ── 店铺账号 ──
        accounts = [
            ShopAccount(platform_id=platforms[0].id, shop_name="旗舰店 A", username_enc=b"enc_user1", password_enc=b"enc_pass1"),
            ShopAccount(platform_id=platforms[0].id, shop_name="旗舰店 B", username_enc=b"enc_user2", password_enc=b"enc_pass2"),
            ShopAccount(platform_id=platforms[1].id, shop_name="自营店铺", username_enc=b"enc_user3", password_enc=b"enc_pass3"),
            ShopAccount(platform_id=platforms[2].id, shop_name="百货专营", username_enc=b"enc_user4", password_enc=b"enc_pass4", status="inactive", health_score=30),
            ShopAccount(platform_id=platforms[3].id, shop_name="品牌旗舰", username_enc=b"enc_user5", password_enc=b"enc_pass5"),
        ]
        session.add_all(accounts)
        await session.flush()

        # ── 存储配置 ──
        storage = StorageConfig(
            type="mysql", name="业务主库",
            config_enc=b"enc_config",
        )
        session.add(storage)
        await session.flush()

        # ── 通知配置 ──
        notification = NotificationConfig(
            channel="feishu",
            webhook_url_enc=b"enc_webhook",
        )
        session.add(notification)
        await session.flush()

        # ── 任务实例 ──
        task_configs = [
            ("订单数据采集", apps[0], accounts[0], "daily-order-sync"),
            ("物流轨迹更新", apps[1], accounts[1], "logistics-track"),
            ("商品库存同步", apps[2], accounts[2], "product-stock-sync"),
            ("退款数据同步", apps[3], accounts[2], "refund-sync"),
            ("评价数据抓取", apps[4], accounts[3], "review-scrape"),
            ("流量数据采集", apps[5], accounts[4], "traffic-analytics"),
        ]

        tasks = []
        for name, app, account, _key in task_configs:
            t = TaskInstance(
                app_id=app.id,
                account_id=account.id,
                storage_config_id=storage.id,
                notification_config_id=notification.id,
                name=name,
                cron_expr="0 8 * * *",
            )
            tasks.append(t)
        session.add_all(tasks)
        await session.flush()

        # ── 执行记录（最近 7 天）──
        now = datetime.now()
        statuses = ["success", "success", "success", "success", "success",
                     "success", "success", "success", "failed"]

        for day_offset in range(7):
            day = now - timedelta(days=6 - day_offset)
            for task in tasks:
                run_status = random.choice(statuses)
                duration = random.randint(2000, 20000) if run_status != "pending" else None
                started = day.replace(hour=8, minute=random.randint(0, 30), second=random.randint(0, 59))
                ended = started + timedelta(milliseconds=duration) if duration else None

                run = TaskRun(
                    task_id=task.id,
                    trigger_type="scheduler",
                    status=run_status,
                    started_at=started,
                    ended_at=ended,
                    duration_ms=duration,
                    error_code="CAPTCHA_EXPIRED" if run_status == "failed" else None,
                    error_message="验证码已过期" if run_status == "failed" else None,
                )
                session.add(run)

        # 今天再加几条特殊状态
        for task, status in [(tasks[1], "running"), (tasks[4], "pending")]:
            session.add(TaskRun(
                task_id=task.id,
                trigger_type="scheduler",
                status=status,
                started_at=now.replace(hour=8, minute=5, second=0),
            ))

        await session.commit()
        print("种子数据写入完成！")


if __name__ == "__main__":
    asyncio.run(seed())

