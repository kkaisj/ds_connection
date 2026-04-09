# ds_connection

数据连接器（DC）项目。

## 开发应用在哪里

### 1. 适配器代码位置（你真正开发业务逻辑的地方）
- `backend/src/infrastructure/connectors/<platform>/`
- 例如：
  - `backend/src/infrastructure/connectors/douyin/traffic_analytics.py`
  - `backend/src/infrastructure/connectors/taobao/order_sync.py`

### 2. 适配器注册位置（不注册就无法发版/上架/执行）
- `backend/src/infrastructure/connectors/base/registry.py`
- 需要新增 `_REGISTRY` 条目：
  - `adapter_key`
  - `class_path`
  - `platform_code`
  - `display_name`（中文名）
  - `description`
  - `default_version`

## 从开发到上架最短流程

1. 在 `connectors` 目录完成适配器实现，并在 `registry.py` 注册。  
2. 发版（写入发布记录）：
```http
POST /api/v1/apps/releases
{
  "adapter_key": "douyin.traffic_analytics",
  "version": "1.1.0",
  "status": "released",
  "qa_passed": true,
  "released_by": "kun-kun"
}
```
3. 上架应用（应用管理页面或接口）时选择该 `adapter_key + version`。  
4. 任务运行时会再次校验发布状态：仅 `released + qa_passed=true` 可执行。  

说明：如果第 2 步没做，上架会被拒绝。

## 页面入口（开发辅助）

- 前端新增“适配器工作台”页面：`/adapter-workbench`
- 用途：开发者代码工作台（代码优先），编写 DrissionPage 自动化脚本并实时预览操作
- 功能：代码编辑、页面预览 iframe、实时操作解析（get/click/input/wait/sleep）、Python 下载
- 注意：该页面不直接写服务端文件，开发完成后仍需把代码落到：
  - `backend/src/infrastructure/connectors/<platform>/`
  - 并在 `backend/src/infrastructure/connectors/base/registry.py` 完成注册

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
