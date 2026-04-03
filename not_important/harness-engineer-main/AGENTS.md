# AGENTS.md

> 本文件是 AI Agent 的核心知识库。Agent 在进行任何操作之前应先阅读本文件。

## 项目概览

<!-- TODO: 替换为你的项目信息 -->
[项目名称] - [一句话描述]

## 架构

### 技术栈
<!-- TODO: 替换为你的实际技术栈 -->
- **前端**: React + Vite + TypeScript
- **后端**: Spring Boot 3 / FastAPI / Node.js
- **数据库**: PostgreSQL / SQLite
- **消息队列**: N/A
- **部署**: Docker + Docker Compose

### 模块与职责

| 模块 | 路径 | 职责 |
|------|------|------|
| <!-- 模块名 --> | `src/module-a/` | <!-- 职责描述 --> |
| <!-- 模块名 --> | `src/module-b/` | <!-- 职责描述 --> |

### 分层规则

```
Controller / Route
    ↓ (只能调用 Service)
Service
    ↓ (只能调用 Repository / 外部 Client)
Repository / Data Access
    ↓
Database
```

- Controller 层：处理 HTTP 请求/响应，参数校验
- Service 层：业务逻辑，事务管理
- Repository 层：数据访问，查询构建

## 约定

### 命名规范
- **文件命名**: kebab-case (`user-profile.ts`) 或 PascalCase (`UserProfile.java`)
- **类命名**: PascalCase (`UserProfileService`)
- **方法命名**: camelCase (`getUserById`)
- **常量命名**: UPPER_SNAKE_CASE (`MAX_RETRY_COUNT`)
- **数据库表**: snake_case (`user_profile`)

### 代码风格
- 使用项目根目录的格式化配置（Prettier / Spotless 等）
- 每个文件应有单一职责
- 方法长度不超过 50 行（建议）
- 使用有意义的变量名，避免缩写

### Git 规范
- Commit Message: `type(scope): description`
  - type: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- 每个 commit 只做一件事

## 禁止操作 ⛔

<!-- TODO: 根据项目调整 -->
- **不要**直接修改数据库 migration 文件（已应用的）
- **不要**在 Controller 层编写业务逻辑
- **不要**在代码中硬编码密钥、密码、Token
- **不要**跳过测试
- **不要**引入循环依赖
- **不要**直接操作 DOM（前端框架项目中）

## 关键文件路径

<!-- TODO: 替换为实际路径 -->
| 用途 | 路径 |
|------|------|
| API 入口 | `src/main/java/com/example/controller/` |
| 配置文件 | `src/main/resources/application.yml` |
| 数据库模型 | `src/main/java/com/example/model/` |
| 测试用例 | `src/test/` |
| 前端入口 | `frontend/src/App.tsx` |
| 环境变量 | `.env.example` |

## 测试策略

### 测试层级
| 类型 | 工具 | 覆盖目标 |
|------|------|---------|
| 单元测试 | JUnit / Jest / pytest | Service 层逻辑 |
| 集成测试 | SpringBootTest / Supertest | API 端点 |
| E2E 测试 | Playwright / Cypress | 用户流程 |

### 运行测试
```bash
# TODO: 替换为你的实际命令
# 运行全部测试
npm test                    # Node.js
./gradlew test              # Java/Kotlin
pytest                      # Python

# 运行特定测试
npm test -- --grep "模式"
./gradlew test --tests "ClassName"
pytest -k "test_name"
```

## 常见问题与陷阱

<!-- TODO: 随项目发展持续补充 -->
1. **[问题描述]** → [解决方案]
2. **[问题描述]** → [解决方案]

## 参考资料

- [架构文档](docs/architecture.md)
- [编码规范](docs/conventions.md)
- [模块边界](docs/module-boundaries.md)
- [Harness Engineering 模版](HARNESS_ENGINEERING_TEMPLATE.md)
