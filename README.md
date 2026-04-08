# ds_connection

数据连接器（DC）项目。

## 启动方式

### 1. 后端
```powershell
cd backend
uv sync
uv run python -m scripts.init_db
uv run uvicorn main:app --app-dir src --reload --port 8000
```

### 2. 前端
```powershell
cd frontend
npm install
npm run dev
```

前端默认访问地址：`http://localhost:5173`  
后端默认访问地址：`http://localhost:8000`

## 详细说明
完整运行说明见：
- `docs/runbook.md`
