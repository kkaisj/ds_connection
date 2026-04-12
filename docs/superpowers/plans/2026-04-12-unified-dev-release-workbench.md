# 统一开发到发版工作台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将“应用开发→编辑→测试→发版”重构为一个开发者优先的统一工作台，并以测试通过为发版前置门槛。  
**Architecture:** 前端重构 `AdapterWorkbench` 为双栏流程化开发台；后端新增 `workbench` 专用接口（创建骨架、保存文件、测试运行）；发版接口增加“最近测试通过”校验；上传层按存储介质策略路由（先支持 mysql）。  
**Tech Stack:** Vue 3 + TypeScript、FastAPI、SQLAlchemy、现有适配器基类与执行上下文。

---

## 文件结构与职责

- 前端页面
  - 修改: `frontend/src/pages/AdapterWorkbench.vue`
  - 作用: 统一工作台 UI（目录/编辑/运行/发版状态）
- 前端类型与请求封装（如项目当前无单独 service，保留在页面内）
  - 修改: `frontend/src/pages/AdapterWorkbench.vue`
  - 作用: 调用新增后端 workbench 接口
- 后端路由
  - 修改: `backend/src/presentation/http/routers/dev_instructions.py`
  - 作用: 新增工作台建骨架、保存、试跑接口
- 后端上传策略
  - 新增: `backend/src/application/services/storage_uploader/base.py`
  - 新增: `backend/src/application/services/storage_uploader/mysql_uploader.py`
  - 新增: `backend/src/application/services/storage_uploader/factory.py`
  - 新增: `backend/src/application/services/file_preprocess/append_columns_processor.py`
  - 新增: `backend/src/application/services/file_preprocess/file_archive_mover.py`
  - 新增: `backend/src/application/services/file_preprocess/pipeline.py`
  - 修改: `backend/src/application/services/data_sink.py`
  - 作用: 上传前执行“批量插入字段 + 文件归档移动”，再按存储介质路由上传（先支持 mysql）
- 下载能力复用
  - 参考: `tools/下载文件/DownAndMoveFile.py`
  - 作用: 页面下载模式下，统一下载并返回处理后文件路径（含下载等待、重命名、目标目录转存）
- 干净浏览器启动能力复用
  - 参考: `tools/chrome/env_chrome.py`
  - 作用: 每次运行走环境隔离浏览器入口（独立 profile、插件加载、窗口句柄校验）
- 接口取数落盘能力复用
  - 参考: `tools/数据保存/SaveToDatabook.py`
  - 作用: 接口直连模式下，将返回数据写入 databook 并导出标准文件回填 `文件路径`
- 后端发版逻辑
  - 修改: `backend/src/presentation/http/routers/marketplace.py`（或当前发版实现所在文件）
  - 作用: 增加“最近测试 success=true”校验
- 文档
  - 修改: `docs/api/openapi.yaml`
  - 修改: `docs/architecture.md`
  - 修改: `docs/runbook.md`
  - 修改: `PROGRESS.json`
  - 作用: 契约、架构、运行手册、进度一致
- 测试
  - 新增: `backend/tests/test_workbench_api.py`
  - 新增: `frontend` 对应页面最小交互测试（若项目已有测试框架）

---

### Task 1: 固化后端 Workbench API（创建骨架/保存/运行）

**Files:**
- Modify: `backend/src/presentation/http/routers/dev_instructions.py`
- Test: `backend/tests/test_workbench_api.py`

- [ ] **Step 1: 写失败测试（骨架生成 + 保存 + 运行）**
- [ ] **Step 2: 实现 `POST /api/v1/dev/workbench/apps/create`**
- [ ] **Step 3: 实现 `PUT /api/v1/dev/workbench/file`**
- [ ] **Step 4: 实现 `POST /api/v1/dev/workbench/run`（默认 real_browser=true）**
- [ ] **Step 4.1: 在运行入口增加启动初始化（清理 Downloads + 清理 WPS 进程）**
- [ ] **Step 4.2: 在运行入口接入 env_chrome 启动流程（替换普通浏览器启动）**
- [ ] **Step 5: 运行后端测试并修正**
- [ ] **Step 6: 提交 Task 1**

验收要点：
- 生成目录包含 `app_main.py/login/collect/schema/tests`
- 保存接口可写入指定文件并做路径安全校验
- 运行接口接收 `input`，返回 `success/rows_count/logs/data_preview`
- 运行结果中的数据对象符合约定：
  - `数据集` 为字符串
  - `待插入字段` 为二维数组（第一行字段名，第二行具体值）
  - `去重主键` 为数组
  - 后端会将中文键映射为内部英文键模型再进入上传层
  - 取数下载动作统一走 `DownAndMoveFile.py` 对应能力封装

---

### Task 2: 重构前端统一工作台（开发优先）

**Files:**
- Modify: `frontend/src/pages/AdapterWorkbench.vue`

- [ ] **Step 1: 重构页面布局为“左代码 + 右流程状态”**
- [ ] **Step 2: 增加三件套编辑入口与多文件切换**
- [ ] **Step 3: 增加统一 input 参数面板**
- [ ] **Step 4: 接入测试运行面板（日志 + 数据预览）**
- [ ] **Step 5: 增加发版状态区（只展示门槛状态，发版动作下个任务接）**
- [ ] **Step 6: 前端构建验证**
- [ ] **Step 7: 提交 Task 2**

验收要点：
- 可在单页面完成三件套开发与测试
- 运行参数包含 `default_download_days` 与 `real_browser`
- 能清晰看到当前阶段（开发中/测试通过/可发版）

---

### Task 3: 发版前置门槛（必须测试通过）

**Files:**
- Modify: `backend/src/presentation/http/routers/marketplace.py`（或发版实现文件）
- Test: `backend/tests/test_release_gate.py`

- [ ] **Step 1: 写失败测试（未通过测试不可发版）**
- [ ] **Step 2: 在发版接口增加校验：最近一次 workbench run success=true**
- [ ] **Step 3: 补充错误码与错误信息**
- [ ] **Step 4: 回归测试（已通过测试可发版）**
- [ ] **Step 5: 提交 Task 3**

验收要点：
- 未通过测试时发版接口拒绝
- 通过测试后可正常发版并记录版本信息

---

### Task 4: 上传策略层（按存储介质路由）

**Files:**
- Create: `backend/src/application/services/storage_uploader/base.py`
- Create: `backend/src/application/services/storage_uploader/mysql_uploader.py`
- Create: `backend/src/application/services/storage_uploader/factory.py`
- Modify: `backend/src/application/services/data_sink.py`
- Test: `backend/tests/test_storage_uploader_mysql.py`

- [ ] **Step 1: 写失败测试（storage.type=mysql 走 mysql uploader）**
- [ ] **Step 2: 定义上传器统一接口（upload(dataset_obj, storage_config, input)）**
- [ ] **Step 2.1: 定义中文键 -> 英文键映射层（adapter DTO）**
- [ ] **Step 3: 实现上传前单文件处理 pipeline（参考 append_columns.py + move_file.py）**
- [ ] **Step 3.1: 实现取数双通道落盘封装（DownAndMoveFile / SaveToDatabook）**
- [ ] **Step 3.2: 统一产出 `文件路径` 并写入数据对象（MVP 多文件时取最新文件）**
- [ ] **Step 4: 实现 mysql uploader（抽取 to_mysql_v2 可复用逻辑）**
- [ ] **Step 5: 在 data_sink 中接入 preprocess pipeline + factory 路由**
- [ ] **Step 6: 预留 feishu/dingtalk 占位上传器接口**
- [ ] **Step 7: 运行测试并修正**
- [ ] **Step 8: 提交 Task 4**

验收要点：
- 当前 mysql 上传可用；
- 当 storage.type 不是 mysql 时，返回明确“未实现”错误；
- 上传器输入支持你的数据对象结构。
- 上传前会产出“原文件路径、处理后文件路径”并进入归档目录。
- 页面下载与接口取数两种模式都能输出统一 `文件路径` 给上传层。
- 应用每次启动前会执行初始化：清理 Downloads 与 WPS 进程清理。
- 浏览器启动必须走环境隔离方案（company/platform/account 维度 profile 隔离）。

---

### Task 5: 文档与契约同步

**Files:**
- Modify: `docs/api/openapi.yaml`
- Modify: `docs/architecture.md`
- Modify: `docs/runbook.md`
- Modify: `PROGRESS.json`

- [ ] **Step 1: OpenAPI 新增 workbench 接口定义与 schema**
- [ ] **Step 2: Architecture 写入统一工作台模型**
- [ ] **Step 3: Runbook 补充开发到发版操作说明**
- [ ] **Step 4: PROGRESS 更新最新能力状态**
- [ ] **Step 5: 提交 Task 5**

---

### Task 6: 联调验收（端到端）

**Files:**
- Verify: `frontend/src/pages/AdapterWorkbench.vue`
- Verify: `backend/src/presentation/http/routers/dev_instructions.py`
- Verify: 发版接口文件

- [ ] **Step 1: 新建一个 demo 应用骨架**
- [ ] **Step 2: 编辑并保存登录/取数/编排文件**
- [ ] **Step 3: 运行测试（success=true）**
- [ ] **Step 4: 发版并确认门槛生效**
- [ ] **Step 5: 检查市场仅展示已发版版本**
- [ ] **Step 6: 记录验收结论并提交 Task 6**

---

## 回归测试清单

- [ ] 后端：`uv run pytest backend/tests/test_workbench_api.py -v`
- [ ] 后端：发版门槛测试（新增文件）通过
- [ ] 后端：上传路由测试（mysql）通过
- [ ] 前端：`npm run build`（必要时设置 `NODE_OPTIONS=--max-old-space-size=6144`）
- [ ] 手工：统一工作台端到端流程可跑通

## 风险与缓解

1. 风险：工作台试跑与线上任务执行链路不一致。  
缓解：试跑复用 `BaseWebDataAdapter + ExecutionContext`，避免双实现。

2. 风险：发版门槛依赖“最近测试记录”定义不清。  
缓解：明确按应用维度保存测试快照并在接口层统一查询。

3. 风险：目录骨架命名不统一导致导入失败。  
缓解：生成时强制 slug 规范化并自动补齐 `__init__.py`。
