# AGENTS.md

## Project
数据连接器（DC）：连接多电商平台，统一采集、调度、入库和告警。

## How To Use This Index
1. 先读本文件，再按任务类型按需读取对应文档。
2. 不要一次性加载全部文档，优先最小上下文。
3. 变更代码后，必须同步更新被影响文档。

## Source Of Truth
1. 架构与分层：`docs/architecture.md`
2. 模块边界与依赖规则：`docs/module-boundaries.md`
3. 编码与测试规范：`docs/conventions.md`
4. API 契约：`docs/api/openapi.yaml`
5. 数据库与索引：`docs/data-model/schema.sql`
6. Harness 运行文件：`.harness/`

## Task Routing
1. 新需求拆解：先读 `.harness/plan.md`，再更新对应 Sprint 合同。
2. 开发实现：读 `docs/architecture.md` + `docs/module-boundaries.md` + `docs/conventions.md`。
3. 接口改动：必须同步 `docs/api/openapi.yaml`。
4. 数据模型改动：必须同步 `docs/data-model/schema.sql`。
5. 提测与验收：按 `.harness/evaluation.md` 打分并记录结论。
6. 会话切换：更新 `.harness/handoff.md`，确保可接续。

## Hard Constraints
1. 分层方向只能是 `presentation -> application -> domain`，`infrastructure` 由 application 调用。
2. 禁止跨 feature 直接依赖内部实现。
3. 所有敏感字段必须加密存储且响应脱敏。
4. 任何“任务执行链路”改动必须补充集成测试。
5. 任何“告警策略”改动必须验证去重和频控。

## Quality Gates
1. Lint/Type Check 必须通过。
2. 单测、集成测试必须通过。
3. 关键链路日志与错误码必须可追踪。
4. 文档一致性检查通过（代码与文档不漂移）。

## Forbidden Actions
1. 不允许绕过模块边界直接访问底层资源。
2. 不允许在 Controller 写业务编排逻辑。
3. 不允许未评估风险就修改调度和重试策略默认值。
