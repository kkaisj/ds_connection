# Runbook

## 环境要求
1. Python 3.12+（项目当前使用 uv 管理）
2. Node.js 18+
3. 可访问 MySQL（配置在 `backend/src/config/settings.py` 或 `.env`）

## 后端启动
```powershell
cd backend
uv sync
uv run python -m scripts.init_db
uv run uvicorn main:app --app-dir src --reload --port 8000
```

说明：
1. `init_db` 会根据当前配置自动建库建表并初始化种子数据（可重复执行）。
2. 当前代码结构已扁平化为 `backend/src/*`，启动入口为 `main:app`，不要再使用 `dc_backend.main:app`。

## 前端启动
```powershell
cd frontend
npm install
npm run dev
```

默认地址：
1. 前端：`http://localhost:5173`
2. 后端：`http://localhost:8000`

## 常见问题
1. 报错 `ModuleNotFoundError: No module named 'dc_backend'`
原因：仍在用旧启动命令。
修复：使用 `uv run uvicorn main:app --app-dir src --reload --port 8000`。

2. 报错 `Can't connect to MySQL server ...`
原因：数据库配置错误或网络不可达。
修复：检查 `backend/src/config/settings.py` 或 `.env` 中 `DC_DB_*` 配置。
