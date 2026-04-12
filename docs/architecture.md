# Architecture

## Overview
DC 采用分层 + 模块化架构，目标是让连接器能力可扩展、任务链路可观测、跨平台适配可维护。

## Layers
1. Presentation：FastAPI Router、Vue 页面、输入输出适配。
2. Application：用例编排、任务调度、事务与重试策略。
3. Domain：实体、值对象、领域规则（不依赖基础设施）。
4. Infrastructure：数据库、DrissionPage、Webhook、缓存、队列。

## Runtime Flow
说明：调度模块以独立 Worker 进程运行（不与 FastAPI API 进程同进程）。
1. Scheduler 触发任务。
2. Task Executor 拉取任务配置和账号凭据。
3. Task Executor 在适配器执行前先做运行初始化（清理 Downloads、清理 WPS 进程）。
4. Connector Adapter 执行平台采集逻辑。
5. Transformer 清洗与标准化为 Canonical Schema。
6. `data_sink.persist_rows` 统一执行文件预处理（批量插入字段、归档）并按存储类型路由上传。
7. Storage Adapter 落库（MySQL 已落地，飞书多维表格/钉钉表格为骨架实现）。
8. Notification 发送告警（按策略去重和频控）。
9. Observability 记录日志、指标、追踪。

## 自动化扩展约定（页面取数）
1. 适配器开发只关注“取数逻辑”，统一继承 `BaseWebDataAdapter`。
2. 登录流程放在 `ensure_login()` 统一入口，避免每个页面重复实现登录编排。
3. 执行核心信息进入全局 `ExecutionContext`（含 credentials/default_download_days/start_date/end_date/run 元数据）。
说明：`start_date/end_date` 由 `default_download_days` 自动换算（默认截止昨天）。
4. `ExecutionContext` 按任务运行单次创建，任务之间不共享上下文对象。
5. 取数流程放在 `collect_rows()`，按页面/场景拆分，便于后续扩展更多页面。
6. 上传/入库由应用层统一入口 `application.services.data_sink.persist_rows` 处理。
7. 浏览器环境由 `isolated_browser` 统一管理：同平台同账号复用已打开 page，不同账号隔离 profile。
8. 隔离浏览器键值统一由 `BaseWebDataAdapter.get_web_page()` 解析，优先级为：
   显式参数 > `app_params` > `ExecutionContext.extra` > 默认值，避免业务适配器硬编码公司/平台/账号。
9. 应用开发采用“指令集编排”：
   登录指令放在 `infrastructure/connectors/login_instructions/`，
   取数指令放在 `infrastructure/connectors/collect_instructions/`，
   具体应用适配器仅负责参数编排与调用指令。
10. 提供“我开发的指令”查询能力（`/api/v1/dev/instructions`），
    用于前端页面展示代码清单并支持点击查看内容（`/api/v1/dev/instructions/content`）。

## Adapter 生命周期（开发 -> 发版 -> 上架 -> 连接 -> 运行）
1. 开发：在 `backend/src/infrastructure/connectors/<platform>/` 编写适配器类。
2. 注册：在 `infrastructure/connectors/base/registry.py` 注册 `adapter_key` 与元数据。
3. 发版：通过 `/api/v1/apps/releases` 写入 `adapter_release` 记录，状态置为 `released` 且 `qa_passed=true`。
4. 上架：`POST /api/v1/apps` 必须绑定已发版版本，否则拒绝上架。
5. 连接：业务侧在连接市场/应用管理选择已上架应用建立任务关系。
6. 运行：`task_executor` 执行前再次校验发布状态，确保线上只跑可发布版本。

## Modules
1. `marketplace`：应用目录、平台分类、连接入口。
2. `account`：店铺账号、凭据管理、账号状态检查。
3. `task`：任务实例、调度配置、触发管理。
4. `execution`：运行状态机、重试、运行日志。
5. `storage`：多目标存储适配器与映射策略。
6. `notification`：通知通道、策略和模板。
7. `admin`：应用上架、模板版本、审核发布。
8. `common`：鉴权、审计、加密、错误码。

## Task Sidebar API
1. 任务右侧侧边栏使用聚合接口 `GET /api/v1/tasks/{id}/sidebar` 拉取参数、存储、最近运行与默认日志。
2. 参数保存走 `PATCH /api/v1/tasks/{id}/sidebar/params`，存储保存走 `PATCH /api/v1/tasks/{id}/sidebar/storage`。
3. 指定运行批次日志走 `GET /api/v1/tasks/{id}/sidebar/logs?run_id=...`。

## Unified Workbench API
1. 统一工作台入口使用 `/api/v1/dev/workbench/*`（apps/create、file、run）。
2. 为兼容旧页面，`/api/v1/dev/instructions/workbench/*` 仍保留。
3. 发版前必须基于工作台测试快照触发门禁校验（`test_snapshot.success=true`）。

## Cross-Cutting
1. Security：凭据加密、最小权限、操作审计。
2. Reliability：超时、重试、熔断、幂等键。
3. Observability：Trace ID 贯穿任务执行全链路。

## SLO (MVP)
1. 任务成功率 >= 95%（7 日滚动）。
2. 失败告警延迟 <= 5 分钟。
3. API P95 <= 300ms（查询型接口）。

## Workbench Model
1. 应用由三部分组成：`登录指令`、`取数指令`、`适配器编排`。
2. 登录与取数分别沉淀在指令集中，适配器只负责参数组织和调用。
3. 工作台以“代码优先”方式开发：先生成三件套，再按文件编辑、保存、测试运行。
4. 测试运行默认 `real_browser=true`，通过统一执行上下文传递账号、日期范围与运行参数。
