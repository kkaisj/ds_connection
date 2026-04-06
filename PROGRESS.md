# DC 数据连接器 - 开发进度跟踪

## 已完成

### Step 1: 后端工程初始化 (2026-04-06)
- pyproject.toml / settings.py / database.py / main.py

### Step 2: 前端工程初始化 (2026-04-06)
- Vite + Vue3 + TypeScript + Naive UI + ECharts
- 奶油暖色调设计系统 + AppLayout 布局

### Step 3: 后端 ORM 模型 + 数据库 (2026-04-06)
- 9 个 ORM 模型 + 软删除字段 (is_deleted)
- Alembic 配置 + SQL 初始化脚本 + 种子数据

### Step 4: 后端看板 API 真实查询 (2026-04-06)
- DashboardService 6 个 DB 查询 + Pydantic Schema

### Step 5: 全部业务页面 (2026-04-06)
- 后端 7 个路由模块 (dashboard/marketplace/tasks/accounts/executions/storages/notifications)
- 前端 8 个页面 (Dashboard/Marketplace/Tasks/Accounts/Executions/Storages/Notifications/Settings)

### Step 6: 完善优化 (2026-04-06)
- **软删除**：所有后端查询加 `is_deleted=False` 过滤，所有业务路由加 `DELETE` 软删除接口
- **全局消息提示**：App.vue 注入 NMessageProvider / NDialogProvider，替换 alert 为 useMessage
- **分页**：任务列表和执行记录加分页组件
- **表单弹窗**：账号管理新增/编辑弹窗，存储管理新增弹窗（按类型动态渲染），通知配置新增弹窗
- **删除操作**：任务/账号/存储/通知都支持前端一键删除
- **DrissionPage 适配器**：ConnectorApp 模型增加 adapter_key 字段，标识浏览器自动化适配器
- **UI 设计文档**：`docs/ui-design.md` 完整的设计规范（配色/字体/阴影/动效/组件/布局）

## 启动方式

### 前置条件
1. MySQL 8.x 已启动
2. 首次建库：`mysql -u root -p123456 --default-character-set=utf8mb4 < backend/scripts/init.sql`
3. 已有库加新字段：
   - `mysql -u root -p dc_connection < backend/scripts/add_soft_delete.sql`
   - `mysql -u root -p dc_connection < backend/scripts/add_adapter_key.sql`

### 后端启动
```bash
cd backend
uv sync
uv run uvicorn dc_backend.main:app --reload --port 8000
```

### 前端启动
```bash
cd frontend
npm install
npm run dev
```

> Vite 代理 `/api` → `localhost:8000`

## 待完成

### 后续功能
- 连接市场：发起连接流程（选应用 → 绑店铺 → 配参数 → 设存储 → 启用）
- DrissionPage 适配器接入：任务执行时根据 adapter_key 调用对应的浏览器自动化脚本
- 系统设置页面：全局策略配置、用户权限管理
- E2E 测试：Playwright 核心流程测试
