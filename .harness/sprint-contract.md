# Sprint Contract

## Sprint
Sprint 1（基础骨架）

## Scope
1. 建立分层目录结构与基础工程配置。
2. 实现 `platform`、`connector_app`、`shop_account` 基础 CRUD。
3. 接入统一响应结构与全局异常处理。
4. 落地基础鉴权和审计日志写入。

## Deliverables
1. 可运行后端服务与基础迁移脚本。
2. OpenAPI 对应接口可调通。
3. 单测与基础集成测试样例。
4. 文档同步更新（架构、边界、规范）。

## Definition Of Done
1. 范围内接口全部可用。
2. Lint、类型检查、单测、集成测试通过。
3. 无阻塞级缺陷（P0/P1）。
4. 关键日志字段可追踪（trace_id/task_id/run_id）。

## Acceptance Cases
1. 创建平台与应用后，可在应用列表查询到数据。
2. 新增店铺账号后，响应中账号字段脱敏。
3. 非法参数返回统一错误结构和业务错误码。
