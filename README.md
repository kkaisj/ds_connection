# ds_connection

数据连接器（DC）项目。

## 项目定位

统一管理电商平台连接能力，覆盖应用上架、任务配置、执行调度、结果回流与告警。

## 快速启动

### 后端
```powershell
cd backend
uv sync
uv run python -m scripts.init_db
uv run uvicorn main:app --app-dir src --reload --port 8000
```

### 调度 Worker（独立进程）
```powershell
cd backend
uv sync
uv run python src/worker.py
```

### 前端
```powershell
cd frontend
npm install
npm run dev
```

- 前端默认地址：`http://localhost:5173`
- 后端默认地址：`http://localhost:8000`
- Worker 与后端 API 分离启动，负责自动调度 `enabled` 状态任务

## 开发者入口

### 适配器代码位置
- `backend/src/infrastructure/connectors/<platform>/`

### 适配器注册位置
- `backend/src/infrastructure/connectors/base/registry.py`

### 开发辅助页面
- 适配器工作台：`/adapter-workbench`
- 用于编写 DrissionPage 脚本、实时查看解析后的操作预览、下载 `.py`
- 该页面不直接写入后端文件系统

## 开发 -> 发版 -> 上架（主链路）

1. 在 `connectors` 目录完成适配器实现，并在 `registry.py` 注册。
2. 通过 `POST /api/v1/apps/releases` 创建发版记录（`released` 且 `qa_passed=true`）。
3. 在应用管理页面上架该 `adapter_key + version`。
4. 任务执行前会再次校验发布状态，不满足发布条件会直接拦截。

## 文档索引

- 运行说明：`docs/runbook.md`
- 架构说明：`docs/architecture.md`
- 模块边界：`docs/module-boundaries.md`
- 规范约束：`docs/conventions.md`
- API 契约：`docs/api/openapi.yaml`
- 数据模型：`docs/data-model/schema.sql`
- 项目进度：`PROGRESS.json`
