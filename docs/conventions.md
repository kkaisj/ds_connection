# Conventions

## General
1. 优先清晰与可维护，避免隐式行为。
2. 代码与文档同步更新，禁止“代码已改文档未变”。
3. 所有公共接口必须有输入校验与错误码。

## Backend
1. Controller 只做参数校验和响应转换，不写业务流程。
2. Service 负责业务编排、事务、重试策略。
3. Repository 仅负责数据访问，不包含业务判断。
4. DTO 与 ORM 实体分离。

## Frontend
1. 页面状态优先局部化，跨页面状态进入 Pinia。
2. 接口类型定义与 OpenAPI 保持一致。
3. 核心页面流程必须有 E2E 用例。

## Error Handling
1. 不允许吞异常。
2. 业务异常和系统异常分离。
3. 返回统一结构：`code/message/data`。

## Logging
1. 结构化日志（JSON）。
2. 每次任务运行必须带 `trace_id`、`task_id`、`run_id`。
3. 不打印密码、token、cookie 等敏感信息。

## Testing
1. 单测：核心服务和领域规则覆盖率 >= 80%。
2. 集成测试：任务执行主链路（调度->采集->落库->告警）。
3. 回归测试：平台适配器更新必须回归历史用例。

## Naming
1. 数据库表与字段使用 `snake_case`。
2. API path 使用复数名词，如 `/tasks`、`/task-runs`。
3. 枚举值使用小写下划线或固定小写单词。
