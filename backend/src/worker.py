"""
DC 任务调度 Worker 入口
以独立进程运行 APScheduler，负责自动调度任务并驱动执行链路。
"""

import asyncio
import logging
import signal

from application.services.task_scheduler import TaskSchedulerService


async def run_worker() -> None:
    """
    启动并阻塞运行调度 Worker。
    支持 Ctrl+C（SIGINT）与 SIGTERM 的优雅退出。
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger = logging.getLogger(__name__)

    scheduler_service = TaskSchedulerService()
    await scheduler_service.start()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop() -> None:
        if not stop_event.is_set():
            logger.info("收到停止信号，准备关闭 Worker")
            stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            # Windows 下信号处理能力有限，KeyboardInterrupt 兜底
            pass

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        logger.info("收到 KeyboardInterrupt，准备关闭 Worker")
    finally:
        await scheduler_service.shutdown()


if __name__ == "__main__":
    asyncio.run(run_worker())
