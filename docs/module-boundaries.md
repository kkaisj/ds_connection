# Module Boundaries

## Dependency Direction
允许依赖：
1. `presentation -> application`
2. `application -> domain`
3. `application -> infrastructure (via interface)`
4. `infrastructure -> domain (仅映射对象)`

禁止依赖：
1. `domain -> application/infrastructure/presentation`
2. `infrastructure -> application`（禁止反向调用 service）
3. `feature A -> feature B internal`（跨模块只能经公开接口）

## Public Contract Rule
每个模块必须提供公开 API（service interface 或 DTO 契约），模块内部实现不可被外部直接引用。

建议目录：
1. `src/<module>/api/*`
2. `src/<module>/internal/*`

## Execution-State Rule
任务状态流转仅允许：
1. `pending -> running`
2. `running -> success|failed|cancelled`
3. `failed -> pending`（仅重试路径）

任何绕过状态机的直接更新都视为违规。

## Storage Rule
1. `task` 模块不得直接写具体存储表。
2. 必须通过 `storage` 适配层统一落库。
3. 目标存储切换不得影响上游采集逻辑。

## Notification Rule
1. 告警发送必须由 `notification` 模块统一出口。
2. 不允许在业务模块直接调用 webhook 客户端。
3. 必须经过频控与去重策略。

## Check List For New Module
1. 是否单一职责。
2. 是否有明确公开接口。
3. 是否满足依赖方向。
4. 是否补充架构边界测试。
