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
6. 项目进度：`PROGRESS.json`
7. Harness 运行文件：`.harness/`

## Collaboration Preferences
1. 默认使用中文回复。
2. 每次回复时称呼用户为【困困】。
3. 需求不明确时，先澄清再改代码。
4. 实施前先给出简短方案，再开始修改。
5. 若一次任务预计修改超过 3 个文件，优先拆成更小步骤再执行。
6. 修复 bug 时，优先补可复现问题的测试，再修复实现。
7. 完成代码后，说明主要风险点，并给出建议测试项。

## Task Routing
1. 新需求拆解：先读 `.harness/plan.md`，再更新对应 Sprint 合同。
2. 开发实现：读 `docs/architecture.md` + `docs/module-boundaries.md` + `docs/conventions.md`。
3. 接口改动：必须同步 `docs/api/openapi.yaml`。
4. 数据模型改动：必须同步 `docs/data-model/schema.sql`。
5. 项目进度更新：统一维护 `PROGRESS.json`，不再维护 `PROGRESS.md`。
6. 提测与验收：按 `.harness/evaluation.md` 打分并记录结论。
7. 会话切换：更新 `.harness/handoff.md`，确保可接续。

## Hard Constraints
1. 分层方向只能是 `presentation -> application -> domain`，`infrastructure` 由 application 调用。
2. 禁止跨 feature 直接依赖内部实现。
3. 所有敏感字段必须加密存储且响应脱敏。
4. 任何“任务执行链路”改动必须补充集成测试。
5. 任何“告警策略”改动必须验证去重和频控。
6. 不主动编写兼容性代码，除非需求明确要求兼容旧逻辑或旧环境。
7. 一次只提问一个问题。根据我的回答，继续追问。直到你有95%的信心理解我的真实需求和目标。然后才给出方案

## Backend Rules
1. SQLAlchemy 查询中不要使用 `.nullslast()` 或 `.nullsfirst()`，项目默认兼容 MySQL 排序行为。
2. ORM 二进制字段使用 `LargeBinary`，不要使用不存在的 `VarBinary`。
3. 所有代码必须写好注释：文件头部说明用途，关键函数、服务和复杂组件应补充中文注释说明职责与核心逻辑。

## Quality Gates
1. Lint/Type Check 必须通过。
2. 单测、集成测试必须通过。
3. 关键链路日志与错误码必须可追踪。
4. 文档一致性检查通过，避免代码与文档漂移。

## Forbidden Actions
1. 不允许绕过模块边界直接访问底层资源。
2. 不允许在 Controller 写业务编排逻辑。
3. 不允许未评估风险就修改调度和重试策略默认值。
4. 不允许把临时纠错记录持续堆积为项目规则；只有稳定、可复用的约束才能写入本文件。
