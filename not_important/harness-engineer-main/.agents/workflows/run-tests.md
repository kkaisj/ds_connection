---
description: 自动化执行测试用例的标准流程
---

# 自动化执行测试用例

// turbo-all

## 步骤

### 1. 确定测试范围

根据变更内容确定需要执行的测试：

| 变更类型 | 需要执行的测试 |
|---|---|
| 后端代码变更 | 后端全量测试（含架构约束） |
| 前端代码变更 | 前端 Lint + 类型检查 + 构建 |
| API 接口变更 | 后端测试 + API 冒烟测试 |
| 全栈变更 | 全部（后端 + 前端 + API 冒烟） |
| 仅文档变更 | 无需测试 |

---

### 2. 后端测试

#### 2.1 运行全量测试（含 ArchUnit 架构约束）

```bash
cd uav-backend && mvn test -B
```

如果测试失败，分析输出并分类：

| 失败类型 | 处理方式 |
|---|---|
| ArchUnit 架构约束 | 检查是否违反了分层规则（见 `docs/architecture/backend-layers.md`） |
| 单元测试 | 检查 Service 层业务逻辑 |
| 编译错误 | 检查类型和导入 |

#### 2.2 运行指定测试类

```bash
cd uav-backend && mvn test -Dtest=ArchitectureTest -B
```

#### 2.3 运行指定测试方法

```bash
cd uav-backend && mvn test -Dtest=ArchitectureTest#controllers_should_not_access_repositories -B
```

---

### 3. 前端测试

#### 3.1 ESLint 代码检查

```bash
cd uav-frontend && npm run lint
```

如果有可自动修复的问题：

```bash
cd uav-frontend && npm run lint:fix
```

#### 3.2 TypeScript 类型检查

```bash
cd uav-frontend && npm run check
```

#### 3.3 构建验证

```bash
cd uav-frontend && npm run build
```

---

### 4. API 冒烟测试

> 前置条件：后端服务已在 `http://localhost:8080` 运行

#### 4.1 运行所有 API 测试

```bash
bash testcases/run-api-tests.sh
```

#### 4.2 运行单个 API 测试

```bash
bash testcases/api/auth.sh
```

```bash
bash testcases/api/user-crud.sh
```

#### 4.3 测试文件索引

| 文件 | 覆盖内容 |
|---|---|
| `testcases/api/auth.sh` | 登录、错误密码、Token 认证、未认证拒绝 |
| `testcases/api/user-crud.sh` | 用户分页查询、角色列表、组织树 |

> 新增 API 接口后，在 `testcases/api/` 下创建对应的测试脚本。

---

### 5. 全量检查（推荐在 PR 前执行）

```bash
bash scripts/agent/run-all-checks.sh
```

---

### 6. 分析测试结果

对于每个失败的测试，按以下步骤处理：

1. **阅读错误信息**：确认失败原因
2. **定位问题代码**：根据堆栈信息找到出错的文件和行号
3. **修复代码**：遵循编码规范（`docs/conventions/`）
4. **重跑失败测试**：确认修复有效
5. **重跑全量测试**：确认没有引入新的回归

### 7. 测试通过确认

所有测试通过后，输出验证总结：

```
✅ 后端测试：X tests passed
✅ ArchUnit 架构约束：12 rules passed
✅ 前端 ESLint：No errors
✅ 前端 TypeScript：No errors
✅ 前端构建：Build successful
✅ API 冒烟测试：X/X passed
```
