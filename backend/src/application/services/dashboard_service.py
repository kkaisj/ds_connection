from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.models import (
    ConnectorApp,
    Platform,
    ShopAccount,
    TaskInstance,
    TaskRun,
)
from presentation.schemas.dashboard import (
    AccountHealth,
    DashboardStats,
    PlatformDistribution,
    PlatformHealth,
    RecentRun,
    TodoItem,
    TrendData,
)


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stats(self) -> DashboardStats:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)
        yesterday_start = today_start - timedelta(days=1)

        # 活跃任务数
        active_tasks = await self.session.scalar(
            select(func.count()).select_from(TaskInstance)
            .where(TaskInstance.status == "enabled", TaskInstance.is_deleted == False)
        ) or 0

        # 上周活跃任务数（近似：用当前值减 delta，这里简化为查一周前的快照）
        # 简化处理：取一周前创建的 enabled 任务数
        active_tasks_last_week = await self.session.scalar(
            select(func.count())
            .select_from(TaskInstance)
            .where(TaskInstance.status == "enabled", TaskInstance.is_deleted == False,
                   TaskInstance.created_at <= week_ago)
        ) or 0

        # 今日成功数
        today_success = await self.session.scalar(
            select(func.count())
            .select_from(TaskRun)
            .where(TaskRun.status == "success", TaskRun.started_at >= today_start)
        ) or 0

        # 昨日成功数
        yesterday_success = await self.session.scalar(
            select(func.count())
            .select_from(TaskRun)
            .where(
                TaskRun.status == "success",
                TaskRun.started_at >= yesterday_start,
                TaskRun.started_at < today_start,
            )
        ) or 0

        # 7日成功率
        runs_7d = await self.session.scalar(
            select(func.count()).select_from(TaskRun).where(TaskRun.started_at >= week_ago)
        ) or 0

        success_7d = await self.session.scalar(
            select(func.count())
            .select_from(TaskRun)
            .where(TaskRun.status == "success", TaskRun.started_at >= week_ago)
        ) or 0

        rate_7d = round((success_7d / runs_7d * 100) if runs_7d > 0 else 0, 1)

        # 前7日成功率
        runs_prev_7d = await self.session.scalar(
            select(func.count())
            .select_from(TaskRun)
            .where(TaskRun.started_at >= two_weeks_ago, TaskRun.started_at < week_ago)
        ) or 0

        success_prev_7d = await self.session.scalar(
            select(func.count())
            .select_from(TaskRun)
            .where(
                TaskRun.status == "success",
                TaskRun.started_at >= two_weeks_ago,
                TaskRun.started_at < week_ago,
            )
        ) or 0

        rate_prev_7d = round((success_prev_7d / runs_prev_7d * 100) if runs_prev_7d > 0 else 0, 1)

        # 异常告警（失败 + 运行中超过30分钟的）
        alert_count = await self.session.scalar(
            select(func.count())
            .select_from(TaskRun)
            .where(
                TaskRun.started_at >= today_start,
                TaskRun.status == "failed",
            )
        ) or 0

        return DashboardStats(
            active_tasks=active_tasks,
            today_success=today_success,
            success_rate_7d=rate_7d,
            alert_count=alert_count,
            active_tasks_delta=active_tasks - active_tasks_last_week,
            today_success_delta=today_success - yesterday_success,
            success_rate_delta=round(rate_7d - rate_prev_7d, 1),
        )

    async def get_trend(self, days: int = 7) -> TrendData:
        now = datetime.now()
        dates: list[str] = []
        success_counts: list[int] = []
        failed_counts: list[int] = []

        for i in range(days):
            day = now - timedelta(days=days - 1 - i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            dates.append(f"{day.month}/{day.day}")

            s = await self.session.scalar(
                select(func.count())
                .select_from(TaskRun)
                .where(
                    TaskRun.status == "success",
                    TaskRun.started_at >= day_start,
                    TaskRun.started_at < day_end,
                )
            ) or 0
            success_counts.append(s)

            f = await self.session.scalar(
                select(func.count())
                .select_from(TaskRun)
                .where(
                    TaskRun.status == "failed",
                    TaskRun.started_at >= day_start,
                    TaskRun.started_at < day_end,
                )
            ) or 0
            failed_counts.append(f)

        return TrendData(dates=dates, success=success_counts, failed=failed_counts)

    async def get_platform_distribution(self) -> list[PlatformDistribution]:
        stmt = (
            select(Platform.name, func.count(TaskInstance.id).label("cnt"))
            .join(ConnectorApp, ConnectorApp.platform_id == Platform.id)
            .join(TaskInstance, TaskInstance.app_id == ConnectorApp.id)
            .where(TaskInstance.status == "enabled", TaskInstance.is_deleted == False)
            .group_by(Platform.name)
            .order_by(func.count(TaskInstance.id).desc())
        )
        result = await self.session.execute(stmt)
        return [PlatformDistribution(name=row.name, value=row.cnt) for row in result]

    async def get_recent_runs(self, limit: int = 10) -> list[RecentRun]:
        stmt = (
            select(TaskRun, TaskInstance, ConnectorApp, ShopAccount, Platform)
            .join(TaskInstance, TaskRun.task_id == TaskInstance.id)
            .join(ConnectorApp, TaskInstance.app_id == ConnectorApp.id)
            .join(ShopAccount, TaskInstance.account_id == ShopAccount.id)
            .join(Platform, ConnectorApp.platform_id == Platform.id)
            .order_by(TaskRun.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        runs: list[RecentRun] = []
        for run, task, app, account, platform in rows:
            runs.append(
                RecentRun(
                    task_name=task.name,
                    task_key=app.name.lower().replace(" ", "-"),
                    platform=platform.name,
                    shop=account.shop_name,
                    status=run.status,
                    duration_ms=run.duration_ms,
                    started_at=run.started_at.isoformat() if run.started_at else "",
                )
            )
        return runs

    async def get_account_health(self) -> AccountHealth:
        total = await self.session.scalar(
            select(func.count()).select_from(ShopAccount)
            .where(ShopAccount.is_deleted == False)
        ) or 0

        healthy = await self.session.scalar(
            select(func.count())
            .select_from(ShopAccount)
            .where(ShopAccount.status == "active", ShopAccount.health_score >= 70,
                   ShopAccount.is_deleted == False)
        ) or 0

        warning = await self.session.scalar(
            select(func.count())
            .select_from(ShopAccount)
            .where(
                ShopAccount.status == "active",
                ShopAccount.health_score < 70,
                ShopAccount.health_score >= 30,
                ShopAccount.is_deleted == False,
            )
        ) or 0

        invalid = total - healthy - warning

        # 每个平台的健康状态（取该平台下最差的账号状态）
        stmt = (
            select(
                Platform.name,
                func.min(ShopAccount.health_score).label("min_score"),
            )
            .join(ShopAccount, ShopAccount.platform_id == Platform.id)
            .where(ShopAccount.is_deleted == False)
            .group_by(Platform.name)
        )
        result = await self.session.execute(stmt)
        platform_health: list[PlatformHealth] = []
        for row in result:
            if row.min_score >= 70:
                status = "healthy"
            elif row.min_score >= 30:
                status = "warning"
            else:
                status = "invalid"
            platform_health.append(PlatformHealth(name=row.name, status=status))

        return AccountHealth(
            total=total,
            healthy=healthy,
            warning=warning,
            invalid=invalid,
            platforms=platform_health,
        )

    async def get_todos(self) -> list[TodoItem]:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        todos: list[TodoItem] = []

        # 1. 失效/异常账号
        stmt = select(ShopAccount, Platform).join(
            Platform, ShopAccount.platform_id == Platform.id
        ).where(ShopAccount.status.in_(["inactive", "disabled"]),
                ShopAccount.is_deleted == False)
        result = await self.session.execute(stmt)
        for account, platform in result:
            todos.append(
                TodoItem(
                    priority="high",
                    text=f"{platform.name}{account.shop_name} - 账号异常，需重新登录",
                    tag="紧急",
                    time="需立即处理",
                )
            )

        # 2. 今日连续失败的任务
        stmt = (
            select(
                TaskInstance.name,
                func.count(TaskRun.id).label("fail_count"),
            )
            .join(TaskRun, TaskRun.task_id == TaskInstance.id)
            .where(TaskRun.status == "failed", TaskRun.started_at >= today_start)
            .group_by(TaskInstance.id, TaskInstance.name)
            .having(func.count(TaskRun.id) >= 1)
        )
        result = await self.session.execute(stmt)
        for row in result:
            todos.append(
                TodoItem(
                    priority="high",
                    text=f"{row.name}任务失败 {row.fail_count} 次",
                    tag="紧急",
                    time="今日",
                )
            )

        # 3. 健康分低的账号
        stmt = select(ShopAccount, Platform).join(
            Platform, ShopAccount.platform_id == Platform.id
        ).where(ShopAccount.status == "active", ShopAccount.health_score < 70,
                ShopAccount.is_deleted == False)
        result = await self.session.execute(stmt)
        for account, platform in result:
            todos.append(
                TodoItem(
                    priority="medium",
                    text=f"{platform.name}{account.shop_name} - 健康分偏低 ({account.health_score})",
                    tag="预警",
                    time="需关注",
                )
            )

        return todos

