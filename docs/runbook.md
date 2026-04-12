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

## 调度 Worker 启动（独立进程）
```powershell
cd backend
uv sync
uv run python src/worker.py
```

说明：
1. Worker 负责自动扫描 `task_instance` 中 `enabled` 任务并按 `cron_expr` 触发。
2. 触发后会创建 `task_run(trigger_type=scheduler)`，并调用现有执行器链路。
3. 建议生产环境将 API 与 Worker 分开部署，避免相互影响。

## DrissionPage 真实浏览器执行
```powershell
cd backend
uv add DrissionPage
```

说明：
1. 任务参数中可配置 `real_browser=true` 启用真实浏览器执行（demo 默认 `false` 为模拟模式）。
2. 任务参数中的 `default_download_days` 会自动换算为 `start_date/end_date`：
   `1` 表示昨天，`3` 表示最近三天（截止昨天）。
3. 环境隔离浏览器由 `infrastructure/connectors/base/isolated_browser.py` 统一管理，
   后续应用可直接通过基类 `get_web_page()` 获取已打开网页对象。
4. 隔离浏览器默认启动入口为仓库文件 `chrome/start.html`；
   若适配器传入 `start_url`，则会优先跳转到业务页面。
5. 如需按任务定制隔离环境，可在任务参数传入：
   `company_name`、`platform_code`、`account_name`、`browser_zoom`。
   若未传入，将自动回退到 `ExecutionContext.extra` 与系统默认值。

## 前端启动
```powershell
cd frontend
npm install
npm run dev
```

默认地址：
1. 前端：`http://localhost:5173`
2. 后端：`http://localhost:8000`

## 我开发的指令页面
1. 路径：`/my-instructions`
2. 用途：查看已开发代码清单（适配器/登录指令/取数指令）、状态、更新时间。
3. 交互：点击列表行可查看代码详情，并可一键跳转到适配器工作台继续编辑。

## 应用开发入口（登录/取数/上传）
1. 应用适配器开发目录：`backend/src/infrastructure/connectors/<platform>/`
2. 登录指令集目录：`backend/src/infrastructure/connectors/login_instructions/`
3. 取数指令集目录：`backend/src/infrastructure/connectors/collect_instructions/`
4. 上传/入库统一入口：`backend/src/application/services/data_sink.py`

## 适配器工作台（纯代码开发）
1. 路径：`/adapter-workbench`
2. 开发模型：一个应用由 `登录指令` + `取数指令` + `适配器编排` 三部分组成。
3. 使用步骤：
   1. 输入 `platform_code` 与 `app_slug`，点击“生成三件套”。
   2. 分别编辑登录、取数、适配器文件并保存。
   3. 配置测试参数（账号、`default_download_days`、`real_browser`）后点击“测试运行”。
4. 后端接口：
   1. `PUT /api/v1/dev/instructions/content`：保存代码。
   2. `POST /api/v1/dev/instructions/workbench/scaffold`：生成三件套。
   3. `POST /api/v1/dev/instructions/workbench/run`：执行测试运行并返回日志与数据预览。

## 常见问题
1. 报错 `ModuleNotFoundError: No module named 'dc_backend'`
原因：仍在用旧启动命令。
修复：使用 `uv run uvicorn main:app --app-dir src --reload --port 8000`。

2. 报错 `Can't connect to MySQL server ...`
原因：数据库配置错误或网络不可达。
修复：检查 `backend/src/config/settings.py` 或 `.env` 中 `DC_DB_*` 配置。
