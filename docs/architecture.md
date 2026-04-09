# Architecture

## Overview
DC 采用分层 + 模块化架构，目标是让连接器能力可扩展、任务链路可观测、跨平台适配可维护。

## Layers
1. Presentation：FastAPI Router、Vue 页面、输入输出适配。
2. Application：用例编排、任务调度、事务与重试策略。
3. Domain：实体、值对象、领域规则（不依赖基础设施）。
4. Infrastructure：数据库、DrissionPage、Webhook、缓存、队列。

## Runtime Flow
1. Scheduler 触发任务。
2. Task Executor 拉取任务配置和账号凭据。
3. Connector Adapter 执行平台采集逻辑。
4. Transformer 清洗与标准化为 Canonical Schema。
5. Storage Adapter 落库（MySQL/飞书/钉钉）。
6. Notification 发送告警（按策略去重和频控）。
7. Observability 记录日志、指标、追踪。

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

## Cross-Cutting
1. Security：凭据加密、最小权限、操作审计。
2. Reliability：超时、重试、熔断、幂等键。
3. Observability：Trace ID 贯穿任务执行全链路。

## SLO (MVP)
1. 任务成功率 >= 95%（7 日滚动）。
2. 失败告警延迟 <= 5 分钟。
3. API P95 <= 300ms（查询型接口）。
