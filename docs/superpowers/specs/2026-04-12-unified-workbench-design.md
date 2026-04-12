# 统一开发到发版工作台设计（严格核对版）

## 0. 核对说明
- 本文按“需求条目 -> 实现证据”逐项核对。
- 结论标记：
- `[x]` 已完成并可在代码中定位。
- `[ ]` 未完成。
- 如与后续用户决策冲突，以最新用户决策为准（例如：浏览器插件加载已改为“不依赖插件”）。

---

## 1. 目标与原则
- [x] 统一“应用开发 + 编辑 + 测试 + 发版”到一个工作台页面。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`
- [x] 发版门禁：必须先测试通过（success=true）才允许发版。
  - 证据：
  - 前端按钮禁用：`frontend/src/pages/AdapterWorkbench.vue`
  - 后端二次校验：`backend/src/presentation/http/routers/marketplace.py`
- [x] 代码优先，不做拖拽。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`
- [x] 输入参数统一进入 `input` 对象。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`
- [x] 上传走统一组件/入口。
  - 证据：`backend/src/application/services/data_sink.py`

---

## 2. 工作台结构

### 2.1 左侧目录树
- [x] 展示应用文件结构（`app_main.py`/`login`/`collect`/`schema`/`tests`）。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`
- [x] 支持目录展开/收起与文件点击打开。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`

### 2.2 中间多标签编辑器
- [x] 支持多文件打开、切换、关闭。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`
- [x] 支持保存当前文件与保存全部。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`

### 2.3 右侧流程面板
- [x] 阶段状态：开发中 -> 测试通过 -> 可发版 -> 已发版。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`
- [x] 参数面板：统一 input 参数编辑。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`
- [x] 测试面板：测试运行、日志、结果预览。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`
- [x] 发版面板：版本号、说明、发版按钮，受门禁控制。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`

---

## 3. 应用运行模型

### 3.1 统一 input 对象
- [x] 包含 `credentials/page_params/default_download_days/runtime/storage`。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`
- [x] `default_download_days` 自动换算 `start_date/end_date`（后端执行上下文）。
  - 证据：
  - `backend/src/infrastructure/connectors/base/execution_context.py`
  - `backend/src/presentation/http/routers/dev_instructions.py`

### 3.2 登录阶段
- [x] 登录指令独立（`login_instructions`）。
  - 证据：`backend/src/infrastructure/connectors/login_instructions/`
- [x] 适配器编排中调用登录指令。
  - 证据：`backend/src/infrastructure/connectors/demo/baidu_hello.py`

### 3.3 启动初始化（固定前置）
- [x] 清理 Downloads。
  - 证据：`backend/src/application/services/runtime_init.py`
- [x] 清理 WPS 进程（wps.exe/wpscloudsvr.exe/et.exe）。
  - 证据：`backend/src/application/services/runtime_init.py`
- [x] 启动隔离浏览器并以 `start.html` 作为入口。
  - 证据：`backend/src/infrastructure/connectors/base/isolated_browser.py`
  - 说明：按最新需求使用 DrissionPage 方案，不依赖插件加载。

### 3.4 取数阶段与数据对象
- [x] 统一返回标准数据对象：
  - `数据集`（字符串）
  - `文件路径`
  - `待插入字段`（二维，第一行字段名、第二行值）
  - `去重主键`
  - 证据：
  - `backend/src/application/services/storage_uploader/base.py`
  - `backend/src/infrastructure/connectors/collect_instructions/demo/baidu_search_collect.py`
- [x] 中文键映射到内部英文模型：
  - `dataset_name/file_path/insert_fields_matrix/dedupe_keys`
  - 证据：`backend/src/application/services/storage_uploader/base.py`

### 3.5 上传阶段
- [x] 统一上传入口（适配器不直接上传）。
  - 证据：`backend/src/application/services/data_sink.py`
- [x] 存储介质路由：
  - `mysql` 可用
  - `feishu_bitable` 骨架
  - `dingtalk_sheet` 骨架
  - 证据：
  - `backend/src/application/services/storage_uploader/factory.py`
  - `backend/src/application/services/storage_uploader/mysql_uploader.py`
  - `backend/src/application/services/storage_uploader/feishu_bitable_uploader.py`
  - `backend/src/application/services/storage_uploader/dingtalk_sheet_uploader.py`

### 3.6 上传前单文件处理
- [x] 批量插入字段（固定前置）。
  - 证据：`backend/src/application/services/file_preprocess/append_columns_processor.py`
- [x] 原文件/处理后文件归档移动。
  - 证据：`backend/src/application/services/file_preprocess/file_archive_mover.py`
- [x] 预处理流水线接入上传主链路。
  - 证据：
  - `backend/src/application/services/file_preprocess/pipeline.py`
  - `backend/src/application/services/data_sink.py`

---

## 4. 发版与市场约束
- [x] 发版记录包含 `version/checksum/released_by/released_at`。
  - 证据：`backend/src/presentation/http/routers/marketplace.py`
- [x] 发版门禁（后端校验）：
  - `status=released` 时必须 `test_snapshot.success=true`
  - 证据：`backend/src/presentation/http/routers/marketplace.py`
- [x] 市场上架仅可使用已发版版本。
  - 证据：`backend/src/presentation/http/routers/marketplace.py`

---

## 5. 最小 API 契约（MVP）
- [x] `POST /api/v1/dev/workbench/apps/create`
- [x] `PUT /api/v1/dev/workbench/file`
- [x] `POST /api/v1/dev/workbench/run`
- [x] `POST /api/v1/apps/releases`
- [x] `GET /api/v1/apps/releases`
- 证据：
- `backend/src/presentation/http/routers/workbench.py`
- `backend/src/main.py`
- `backend/src/presentation/http/routers/marketplace.py`

---

## 6. 连接任务右侧侧边栏联动
- [x] 聚合接口：参数 + 存储 + 最近执行 + 默认日志
  - `GET /api/v1/tasks/{id}/sidebar`
- [x] 参数保存接口
  - `PATCH /api/v1/tasks/{id}/sidebar/params`
- [x] 存储保存接口
  - `PATCH /api/v1/tasks/{id}/sidebar/storage`
- [x] 指定批次日志接口
  - `GET /api/v1/tasks/{id}/sidebar/logs?run_id=...`
- [x] 前端侧边栏联动接入
  - 证据：
  - `backend/src/presentation/http/routers/tasks.py`
  - `frontend/src/pages/Tasks.vue`

---

## 7. 验收条目核对
- [x] 单页完成：新建骨架、编辑、测试、发版。
  - 证据：`frontend/src/pages/AdapterWorkbench.vue`
- [x] 三段式模型：登录、取数、上传编排。
  - 证据：
  - `backend/src/infrastructure/connectors/demo/baidu_hello.py`
  - `backend/src/application/services/data_sink.py`
- [x] `default_download_days` 参与运行并生成日期范围。
  - 证据：
  - `backend/src/infrastructure/connectors/base/execution_context.py`
  - `backend/src/presentation/http/routers/dev_instructions.py`
- [x] 未测试通过时发版按钮不可用（前端）+ 后端拦截（双保险）。
  - 证据：
  - `frontend/src/pages/AdapterWorkbench.vue`
  - `backend/src/presentation/http/routers/marketplace.py`
- [x] 上传层按 `input.storage.type` 路由（当前 mysql 可用）。
  - 证据：`backend/src/application/services/storage_uploader/factory.py`
- [x] 上传前执行“批量插入字段 + 归档”。
  - 证据：
  - `backend/src/application/services/file_preprocess/pipeline.py`
  - `backend/src/application/services/data_sink.py`

---

## 8. 当前结论
- [x] 本规范中的 MVP 必要项已完成并可定位到实现文件。
- [x] 已完成项已全部勾选。
