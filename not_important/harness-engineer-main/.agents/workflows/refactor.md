---
description: 代码重构的标准流程
---

# 代码重构

## 步骤

### 1. 理解现有代码

- 阅读相关模块的架构文档（`docs/architecture/`）
- 理解当前实现的职责和依赖关系
- 确认重构范围和目标

### 2. 制定重构方案

- 确保重构不改变外部行为
- 遵循分层架构约束（`docs/architecture/backend-layers.md` / `frontend-layers.md`）
- 遵循命名规范（`docs/conventions/naming-conventions.md`）

### 3. 执行重构

- 分步骤执行，每步保持可编译
- 重构顺序建议：
  1. 重命名 / 移动文件
  2. 提取方法 / 类
  3. 调整依赖关系
  4. 清理未使用的代码

### 4. 验证

// turbo
```bash
cd uav-backend && mvn test -B
```

// turbo
```bash
cd uav-frontend && npm run lint && npm run check && npm run build
```

确保 ArchUnit 架构约束测试仍然通过。

### 5. 更新文档

- 如果重构涉及架构变更，更新 `docs/architecture/` 相关文档
- 如果重构涉及 API 变更，更新 `docs/references/api-reference.md`
- 如果新增包或模块，更新 `AGENTS.md` 中的项目结构

### 6. 自查清单

- [ ] 外部行为未改变
- [ ] 所有测试通过
- [ ] 架构约束检查通过
- [ ] 类型检查通过
- [ ] 文档已同步更新
