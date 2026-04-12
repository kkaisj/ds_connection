"""
任务调度服务测试
覆盖独立 Worker 的关键链路：调度触发后创建 TaskRun 并调用执行器。
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from application.services.task_scheduler import TaskSchedulerService
from infrastructure.persistence.models.models import TaskInstance, TaskRun


class _FakeSession:
    """简化版异步会话，用于调度服务单测。"""

    def __init__(self, task: TaskInstance, running_run_id: int | None = None) -> None:
        self.task = task
        self.running_run_id = running_run_id
        self.created_runs: list[TaskRun] = []
        self._next_run_id = 100

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, model, pk):
        if model is TaskInstance and pk == self.task.id:
            return self.task
        if model is TaskRun:
            for run in self.created_runs:
                if run.id == pk:
                    return run
        return None

    async def scalar(self, stmt):
        return self.running_run_id

    def add(self, obj):
        if isinstance(obj, TaskRun):
            obj.id = self._next_run_id
            self._next_run_id += 1
            self.created_runs.append(obj)

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None


@pytest.mark.asyncio
async def test_scheduler_job_creates_run_and_calls_executor(monkeypatch) -> None:
    """调度触发时应创建 scheduler 类型运行记录并调用执行器。"""
    task = SimpleNamespace(id=1, status="enabled", is_deleted=False, cron_expr="*/5 * * * *")
    fake_session = _FakeSession(task=task)
    def fake_factory():
        return fake_session

    service = TaskSchedulerService(session_factory=fake_factory)
    mock_execute = AsyncMock()
    mock_sync = AsyncMock()
    monkeypatch.setattr("application.services.task_scheduler.execute_task_run", mock_execute)
    monkeypatch.setattr(service, "_sync_next_run_at", mock_sync)

    await service._run_task_job(task_id=1)

    assert len(fake_session.created_runs) == 1
    run = fake_session.created_runs[0]
    assert run.task_id == 1
    assert run.trigger_type == "scheduler"
    assert run.status == "pending"
    assert run.idempotency_key.startswith("scheduler:1:")
    mock_execute.assert_awaited_once()
    mock_sync.assert_awaited_once()


@pytest.mark.asyncio
async def test_scheduler_job_skips_when_existing_run(monkeypatch) -> None:
    """存在 pending/running 时应跳过本轮调度，避免并发堆积。"""
    task = SimpleNamespace(id=2, status="enabled", is_deleted=False, cron_expr="*/5 * * * *")
    fake_session = _FakeSession(task=task, running_run_id=999)
    def fake_factory():
        return fake_session

    service = TaskSchedulerService(session_factory=fake_factory)
    mock_execute = AsyncMock()
    mock_sync = AsyncMock()
    monkeypatch.setattr("application.services.task_scheduler.execute_task_run", mock_execute)
    monkeypatch.setattr(service, "_sync_next_run_at", mock_sync)

    await service._run_task_job(task_id=2)

    assert fake_session.created_runs == []
    mock_execute.assert_not_awaited()
    mock_sync.assert_awaited_once()
