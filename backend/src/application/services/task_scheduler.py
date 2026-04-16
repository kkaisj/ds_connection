"""
任务调度服务
负责以独立 Worker 进程方式维护 APScheduler 任务，
并在触发时创建 task_run 记录后调用执行器完成采集链路。
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from application.services.task_executor import execute_task_run
from config.database import async_session_factory, dispose_database_engine
from infrastructure.persistence.models.models import TaskInstance, TaskRun

logger = logging.getLogger(__name__)


class TaskSchedulerService:
    """
    任务调度服务。

    核心职责：
    1. 周期性扫描数据库中的启用任务；
    2. 将 cron 表达式同步为 APScheduler Job；
    3. 到点后创建 scheduler 类型 TaskRun 并驱动执行器；
    4. 回写 task_instance.next_run_at 便于前端展示下一次调度时间。
    """

    JOB_PREFIX = "task_instance:"
    REFRESH_JOB_ID = "task_scheduler:refresh_jobs"

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        refresh_interval_sec: int = 30,
        default_timezone: str = "Asia/Shanghai",
    ) -> None:
        self._session_factory = session_factory or async_session_factory
        self._refresh_interval_sec = refresh_interval_sec
        self._default_timezone = default_timezone
        self._scheduler = AsyncIOScheduler(timezone=default_timezone)
        self._signatures: dict[int, str] = {}

    @property
    def scheduler(self) -> AsyncIOScheduler:
        """暴露调度器对象，方便测试与运行态观测。"""
        return self._scheduler

    async def start(self) -> None:
        """启动调度器并立即执行一次任务同步。"""
        if self._scheduler.running:
            return

        self._scheduler.add_job(
            self.refresh_jobs,
            "interval",
            seconds=self._refresh_interval_sec,
            id=self.REFRESH_JOB_ID,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        await self.refresh_jobs()
        self._scheduler.start()
        logger.info("任务调度服务已启动")

    async def shutdown(self) -> None:
        """优雅关闭调度器。"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        # 关闭连接池，避免事件循环结束后 aiomysql 析构告警
        await dispose_database_engine()
        logger.info("任务调度服务已关闭")

    async def refresh_jobs(self) -> None:
        """
        同步数据库任务到 APScheduler。

        增量策略：
        1. 仅为 enabled 且未软删除任务注册 Job；
        2. 若 cron/timezone 变化则替换 Job；
        3. 对已停用或删除任务移除 Job；
        4. 同步 next_run_at，保证前端显示与真实调度一致。
        """
        tasks = await self._load_enabled_tasks()
        active_ids = {task.id for task in tasks}
        changed_task_ids: set[int] = set()

        for task in tasks:
            trigger = self._build_trigger(task.cron_expr, task.timezone or self._default_timezone)
            if trigger is None:
                changed_task_ids.add(task.id)
                continue

            job_id = self._job_id(task.id)
            signature = f"{task.cron_expr}|{task.timezone or self._default_timezone}"
            exists = self._scheduler.get_job(job_id) is not None

            if self._signatures.get(task.id) != signature or not exists:
                self._scheduler.add_job(
                    self._run_task_job,
                    trigger=trigger,
                    id=job_id,
                    kwargs={"task_id": task.id},
                    replace_existing=True,
                    coalesce=True,
                    max_instances=1,
                    misfire_grace_time=120,
                )
                self._signatures[task.id] = signature
                changed_task_ids.add(task.id)

        # 清理失效 job（任务被暂停/删除）
        stale_ids = [task_id for task_id in self._signatures if task_id not in active_ids]
        for task_id in stale_ids:
            self._scheduler.remove_job(self._job_id(task_id))
            self._signatures.pop(task_id, None)
            changed_task_ids.add(task_id)

        if changed_task_ids:
            await self._sync_next_run_at(changed_task_ids)

    async def _load_enabled_tasks(self) -> list[TaskInstance]:
        """加载当前启用且未删除的任务。"""
        async with self._session_factory() as session:
            stmt = select(TaskInstance).where(
                TaskInstance.is_deleted.is_(False),
                TaskInstance.status == "enabled",
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def _run_task_job(self, task_id: int) -> None:
        """
        APScheduler 触发回调。
        创建 scheduler 类型 task_run，然后沿用现有执行器。
        """
        async with self._session_factory() as session:
            task = await session.get(TaskInstance, task_id)
            if not task or task.is_deleted or task.status != "enabled":
                logger.info("跳过调度：任务不存在或已停用 task_id=%s", task_id)
                await self._sync_next_run_at({task_id})
                return

            # 防止同一任务并发堆积：存在 pending/running 时跳过当前轮次
            running_stmt = (
                select(TaskRun.id)
                .where(
                    TaskRun.task_id == task_id,
                    TaskRun.status.in_(["pending", "running"]),
                )
                .limit(1)
            )
            running_run_id = await session.scalar(running_stmt)
            if running_run_id:
                logger.warning(
                    "任务仍在执行，跳过本次调度 task_id=%s run_id=%s",
                    task_id,
                    running_run_id,
                )
                await self._sync_next_run_at({task_id})
                return

            now = datetime.now()
            run = TaskRun(
                task_id=task_id,
                trigger_type="scheduler",
                status="pending",
                started_at=now,
                idempotency_key=f"scheduler:{task_id}:{now:%Y%m%d%H%M%S}",
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)

            try:
                await execute_task_run(session, run.id)
            except Exception:
                logger.exception("调度执行异常 task_id=%s run_id=%s", task_id, run.id)
                latest = await session.get(TaskRun, run.id)
                if latest and latest.status in ("pending", "running"):
                    latest.status = "failed"
                    latest.ended_at = datetime.now()
                    latest.error_code = "SCHEDULER_EXCEPTION"
                    latest.error_message = "调度器触发执行异常"
                    await session.commit()

        await self._sync_next_run_at({task_id})

    def _build_trigger(self, cron_expr: str, timezone: str) -> CronTrigger | None:
        """将 cron 表达式解析为 APScheduler 触发器。"""
        try:
            return CronTrigger.from_crontab(cron_expr, timezone=timezone)
        except ValueError:
            logger.error("非法 cron 表达式，跳过调度 cron=%s timezone=%s", cron_expr, timezone)
            return None

    def _job_id(self, task_id: int) -> str:
        """统一生成 job_id，便于维护与排障。"""
        return f"{self.JOB_PREFIX}{task_id}"

    async def _sync_next_run_at(self, task_ids: set[int]) -> None:
        """将 APScheduler 计算结果回写到 task_instance.next_run_at。"""
        if not task_ids:
            return

        async with self._session_factory() as session:
            stmt = select(TaskInstance).where(TaskInstance.id.in_(task_ids))
            result = await session.execute(stmt)
            tasks = result.scalars().all()

            for task in tasks:
                job = self._scheduler.get_job(self._job_id(task.id))
                # APScheduler 不同版本/状态下 Job 可能暂未暴露 next_run_time，统一兜底为 None
                task.next_run_at = getattr(job, "next_run_time", None) if job else None
            await session.commit()
