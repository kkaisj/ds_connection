---
description: 初始化项目的 Harness Engineering 基础设施（从模版套用到具体项目）
---

# 初始化 Harness Engineering

当你需要将 Harness Engineering 模版套用到一个新项目时，按以下步骤操作：

## 前提条件
- 项目已有基本的代码结构
- 已确定技术栈

## 步骤

### 1. 定制 AGENTS.md
// turbo
阅读 `HARNESS_ENGINEERING_TEMPLATE.md` 中的指导，根据实际项目修改 `AGENTS.md`：
- 替换项目名称和描述
- 填写实际技术栈
- 填写模块与职责
- 填写关键文件路径
- 列出项目特有的禁止操作

### 2. 定制架构文档
根据实际项目修改 `docs/architecture.md`：
- 更新系统架构图
- 填写实际模块划分
- 更新 API 设计规范
- 设定性能目标

### 3. 定制编码规范
根据实际项目修改 `docs/conventions.md`：
- 确认前端/后端规范适用
- 调整测试覆盖率目标
- 添加项目特有的规范

### 4. 定制模块边界
根据实际项目修改 `docs/module-boundaries.md`：
- 更新实际模块列表
- 确认依赖方向规则
- 编写对应的结构测试

### 5. 定制评估标准
根据项目类型修改 `.harness/criteria/evaluation-criteria.md`：
- 调整各维度的权重和阈值
- 如果是内部工具，降低设计质量权重
- 如果是面向用户的产品，提高设计质量和原创性权重
- 添加项目特有的评估维度（如可访问性、性能等）

### 6. 配置 Linter 和结构测试
根据技术栈安装对应的约束工具：
- **Java**: 添加 ArchUnit 依赖，编写结构测试
- **TypeScript**: 配置 eslint-plugin-import 的 restricted-paths
- **Python**: 配置 import-linter

### 7. 验证
运行以下检查确认所有文件就位：
```bash
# 检查文件结构
find . -name "*.md" -path "./.harness/*" -o -name "AGENTS.md" -o -name "*.md" -path "./docs/*" | sort

# 确认所有 TODO 已替换
grep -rn "TODO" AGENTS.md docs/ .harness/ || echo "✅ 没有遗留的 TODO"
```
