# 编码规范

> 本文档定义项目的编码规范。所有代码（人工或 AI 生成）都必须遵循这些规范。
> 规范通过 Linter 和结构测试**机械化执行**，而不仅仅依赖口头约定。

## 通用规范

### 文件组织
- 每个文件只包含一个主要的类/组件/模块
- 文件名应能反映其内容
- 相关文件放在同一目录下
- 测试文件与源文件保持相同目录结构

### 注释
- 代码应自解释，避免冗余注释
- 复杂业务逻辑必须添加注释说明 **为什么**（而非做什么）
- 公共 API 必须有文档注释
- TODO 格式: `// TODO(owner): description`

### 错误处理
- 不要吞掉异常（empty catch block）
- 使用自定义异常类区分业务错误和系统错误
- 始终记录错误日志
- API 层统一错误处理（全局异常处理器）

---

## 前端规范

### 组件设计
```
components/
├── common/          # 可复用的通用组件
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.css
│   │   └── Button.test.tsx
│   └── ...
├── features/        # 业务组件
│   ├── UserProfile/
│   └── ...
└── layouts/         # 布局组件
    └── ...
```

- 组件使用 **PascalCase** 命名
- 每个组件有独立目录，包含组件文件、样式、测试
- Props 使用 TypeScript 接口定义
- 避免组件超过 200 行

### 状态管理
- 局部状态优先使用组件内 state
- 跨组件共享状态使用 Store（Zustand / Pinia / Redux 等）
- Store 不应在组件外直接操作（通过 Action/Mutation）

### 样式
- 使用 CSS Modules 或 scoped CSS 避免全局污染
- 使用 CSS 变量定义设计 Token（颜色、间距、字体等）
- 响应式设计使用 `rem`/`em` 而非 `px`

---

## 后端规范

### 分层职责

#### Controller 层
```
✅ 接收和校验请求参数
✅ 调用 Service 层
✅ 返回统一格式的响应
❌ 不包含业务逻辑
❌ 不直接访问数据库
❌ 不调用外部服务
```

#### Service 层
```
✅ 实现业务逻辑
✅ 事务管理
✅ 调用 Repository 或外部 Client
❌ 不处理 HTTP 请求/响应
❌ 不构造 HTTP 状态码
```

#### Repository 层
```
✅ 数据库访问
✅ 查询构建
❌ 不包含业务逻辑
❌ 不调用其他 Service
```

### DTO 设计
- 使用独立的 Request / Response DTO
- DTO 不复用为数据库实体
- 数据转换在 Service 层完成

```
dto/
├── request/
│   ├── CreateUserRequest.java
│   └── UpdateUserRequest.java
└── response/
    ├── UserResponse.java
    └── UserListResponse.java
```

### 日志
- 使用结构化日志（JSON 格式优先）
- 日志级别:
  - `ERROR`: 需要立即处理的系统错误
  - `WARN`: 异常但可恢复的情况
  - `INFO`: 关键业务流程节点
  - `DEBUG`: 调试信息（生产环境关闭）
- 日志中不记录敏感数据

---

## 数据库规范

### 命名
- 表名: `snake_case`, 复数形式 (`users`, `user_profiles`)
- 列名: `snake_case` (`created_at`, `user_id`)
- 索引名: `idx_{table}_{column}` (`idx_users_email`)
- 外键名: `fk_{table}_{ref_table}` (`fk_orders_users`)

### Migration
- 每次变更创建新的 migration 文件
- Migration 必须可逆（提供 up 和 down）
- 不修改已应用的 migration

---

## 测试规范

### 测试命名
```
// 格式: should_[期望行为]_when_[前置条件]
should_return_user_when_valid_id_provided()
should_throw_exception_when_user_not_found()
```

### 测试结构 (AAA)
```
// Arrange - 准备测试数据
// Act     - 执行被测方法
// Assert  - 验证结果
```

### 覆盖率目标
| 层级 | 覆盖率 |
|------|--------|
| Service 层 | ≥ 80% |
| Repository 层 | ≥ 70% |
| Controller 层 | ≥ 60% |
| 工具类 | ≥ 90% |
