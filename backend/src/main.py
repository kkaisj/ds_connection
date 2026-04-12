"""
DC 数据连接器 - FastAPI 应用入口
注册所有路由模块和中间件。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from presentation.http.routers import (
    accounts,
    dashboard,
    dev_instructions,
    executions,
    marketplace,
    notifications,
    storages,
    tasks,
    workbench,
)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    # CORS 中间件：允许前端开发服务器跨域请求
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由模块
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
    app.include_router(marketplace.router, prefix="/api/v1/apps", tags=["apps"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
    app.include_router(executions.router, prefix="/api/v1/task-runs", tags=["task-runs"])
    app.include_router(storages.router, prefix="/api/v1/storages", tags=["storages"])
    app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
    app.include_router(dev_instructions.router, prefix="/api/v1/dev/instructions", tags=["dev"])
    app.include_router(workbench.router, prefix="/api/v1/dev/workbench", tags=["workbench"])

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

