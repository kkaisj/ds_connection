---
description: 修复 Bug 的标准流程
---

# 修复 Bug

## 步骤

### 1. 理解问题

- 确认 Bug 的复现步骤
- 确认影响范围（前端/后端/数据库）
- 阅读相关模块的文档（`docs/architecture/`, `AGENTS.md`）

### 2. 定位问题

- 使用搜索工具在代码中定位相关文件
- 检查相关的 Controller → Service → Repository 调用链
- 检查前端对应的 views → api → store 调用链

### 3. 编写修复

- 遵循现有编码规范（`docs/conventions/`）
- 只修改必要的代码，最小化变更范围
- 添加代码注释说明修复原因

### 4. 验证修复

// turbo
```bash
cd uav-backend && mvn test -B
```

// turbo
```bash
cd uav-frontend && npm run lint && npm run check && npm run build
```

### 5. 手动验证

- 启动前后端服务
- 按照复现步骤验证 Bug 已修复
- 验证相关功能没有回归问题

### 6. 更新文档（如需要）

- 如果修复涉及 API 变更，更新 `docs/references/api-reference.md`
- 如果修复涉及架构变更，更新相关架构文档
