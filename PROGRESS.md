# DC 数据连接器开发进度

## 已完成

### Step 1: 项目基础骨架初始化（2026-04-06）
- 完成前后端分离目录结构：`backend`、`frontend`、`docs`
- 后端完成 `pyproject.toml`、`uv.lock`、`alembic.ini`、`src/dc_backend` 基础工程搭建
- 前端完成 `Vite + Vue 3 + TypeScript` 初始化
- 补充项目根目录 `.gitignore`

### Step 2: 后端基础能力搭建（2026-04-06）
- FastAPI 应用入口已完成，主入口位于 `backend/src/dc_backend/main.py`
- 完成配置与基础模块：`config`、`common`、`presentation`、`application`、`infrastructure`
- 已注册 7 组业务 API 路由：
  - `dashboard`
  - `apps`
  - `tasks`
  - `accounts`
  - `task-runs`
  - `storages`
  - `notifications`
- 已整理 OpenAPI 文档：`docs/api/openapi.yaml`

### Step 3: 数据库与模型设计落地（2026-04-06）
- 已完成 Alembic 迁移目录与初始化配置
- 已提供数据库初始化脚本：`backend/scripts/init.sql`
- 已提供种子数据脚本：`backend/scripts/seed_demo_data.py`
- 已补充多份增量 SQL 脚本：
  - `add_soft_delete.sql`
  - `add_adapter_key.sql`
  - `add_captcha.sql`
  - `alter_storage_type.sql`
- ORM 模型已落地，覆盖平台、连接应用、店铺账号、任务实例、任务运行、存储配置、通知配置等核心对象

### Step 4: 后端核心业务能力（2026-04-06）
- Dashboard 查询服务已实现，包含统计、趋势、平台分布、最近执行、账号健康、待办等接口
- 任务管理已支持：
  - 列表查询
  - 新建
  - 编辑
  - 软删除
  - 手动执行
  - 重试
- 账号管理已支持：
  - 列表查询
  - 新建
  - 编辑
  - 软删除
  - 验证码转发配置
- 存储管理已支持列表、新建、编辑、软删除
- 通知配置已支持列表、新建、编辑、软删除
- 执行记录已支持列表查询与日志查看
- 连接市场已支持应用列表、平台列表、应用详情、软删除

### Step 5: 适配器与任务执行链路（2026-04-06）
- 已加入 `adapter_key` 字段，用于将连接应用映射到具体采集适配器
- 已实现任务执行服务 `task_executor`
- 已实现 DrissionPage 适配器注册与查找机制
- 当前已落地 6 个适配器示例：
  - `taobao.order_sync`
  - `taobao.logistics_track`
  - `jd.product_stock_sync`
  - `jd.refund_sync`
  - `pdd.review_scrape`
  - `douyin.traffic_analytics`

### Step 6: 数据一致性与删除策略（2026-04-06）
- 业务核心表已加入 `is_deleted` 软删除字段
- 任务、账号、应用、存储、通知等业务查询已统一过滤 `is_deleted = False`
- 删除接口均改为软删除，不做物理删除

### Step 7: 验证码转发配置（2026-04-06）
- 店铺账号模型已支持验证码相关字段：
  - `captcha_method`
  - `captcha_config`
  - `captcha_enabled`
- 前后端已打通验证码配置录入与展示
- 已支持的验证码方式包括：
  - `none`
  - `sms_forward`
  - `email_forward`
  - `email_auth_code`
  - `manual`

### Step 8: 前端业务页面与交互（2026-04-06）
- 已完成应用主布局 `AppLayout`
- 已完成 8 个前端页面：
  - `Dashboard`
  - `Marketplace`
  - `Tasks`
  - `Accounts`
  - `Executions`
  - `Storages`
  - `Notifications`
  - `Settings`
- 已实现基础路由与页面导航
- 已补充通用组件：
  - `DcConfirm`
  - `DcSelect`
- 已接入全局消息提示与对话框能力
- 任务列表与执行记录已具备分页
- 账号、存储、通知等页面已具备弹窗表单交互

### Step 9: 设计与文档补充（2026-04-06）
- 已完成后端架构文档：`docs/architecture.md`
- 已完成模块边界文档：`docs/module-boundaries.md`
- 已完成工程约定文档：`docs/conventions.md`
- 已完成 UI 设计文档：`docs/ui-design.md`
- 已补充产品方案文档中的后端目录结构细化说明
- 已保留设计原型文件：`dashboard-prototype.html`

## 当前启动方式

### 前置条件
1. 启动 MySQL 8.x
2. 首次建库初始化：
```bash
mysql -u root -p123456 --default-character-set=utf8mb4 < backend/scripts/init.sql
```
3. 若历史库需要补字段，可执行：
```bash
mysql -u root -p dc_connection < backend/scripts/add_soft_delete.sql
mysql -u root -p dc_connection < backend/scripts/add_adapter_key.sql
mysql -u root -p dc_connection < backend/scripts/add_captcha.sql
```

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

> 前端通过 Vite 代理 `/api` 到 `http://localhost:8000`

## 待完成

### 高优先级
- 打通“连接应用 -> 绑定店铺 -> 配置任务 -> 设置存储 -> 启用执行”的完整业务闭环
- 将任务执行链路与真实 DrissionPage 浏览器自动化流程完全接通
- 完成通知发送通道的真实 webhook 集成，而不只是配置管理
- 增补系统设置页的真实后端接口与持久化配置

### 中优先级
- 增加更多平台适配器与适配器回归测试
- 完善任务调度、失败重试、幂等控制与告警策略
- 补充更完整的 API 文档与示例请求
- 梳理数据库迁移版本与初始化脚本的关系，统一演进方式

### 测试与质量
- 补充后端单元测试与集成测试
- 补充前端关键页面测试
- 增加 Playwright E2E 主流程测试
- 完善日志、追踪、异常监控与运行健康检查
