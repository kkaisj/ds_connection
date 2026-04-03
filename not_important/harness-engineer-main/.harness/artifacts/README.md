# Harness Artifacts

> 此目录存放 Agent 间通信产生的文件。
>
> 文件由 Agent 运行时自动生成，不需要手动创建。

## 文件说明

| 文件 | 生成者 | 说明 |
|------|--------|------|
| `plan.md` | Planner | 产品规格文档 |
| `sprint-contract-N.md` | Generator + Evaluator | Sprint N 的协商契约 |
| `sprint-contract-current.md` | 编排器 | 当前 Sprint 的契约（软链接或复制） |
| `implementation-notes-N.md` | Generator | Sprint N 的实现说明 |
| `evaluation-N.md` | Evaluator | Sprint N 的评估报告 |
| `handoff.md` | 当前 Agent | Session 间状态移交 |
| `final-report.md` | Evaluator | 最终评估报告 |
