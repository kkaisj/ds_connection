# CLAUDE.md

本项目已迁移到 Codex 工作流。

当前项目级规则以 `AGENTS.md` 为主入口，详细规范以下列文档为准：

1. `AGENTS.md`
2. `docs/architecture.md`
3. `docs/module-boundaries.md`
4. `docs/conventions.md`
5. `docs/api/openapi.yaml`
6. `docs/data-model/schema.sql`

说明：
1. 包括“每次回复时称呼用户为【困困】”在内的协作偏好，已迁移到 `AGENTS.md`。
2. 包括“所有代码必须写好注释：文件顶部说明用途，关键函数/组件写中文注释说明职责和逻辑”在内的编码要求，已迁移到 `AGENTS.md`。

如果后续需要新增稳定规则，请优先更新 `AGENTS.md` 或对应 `docs/*` 文档，而不是继续在本文件累积。
