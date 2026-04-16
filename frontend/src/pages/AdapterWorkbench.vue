<!--
  页面用途：
  1. 统一“应用开发 -> 编辑 -> 测试 -> 发版”在一个工作台完成。
  2. 提供左侧目录树、中间多标签编辑器、右侧阶段与运行状态面板。
  3. 严格执行发版门禁：测试 success=true 前不可发版。
-->
<template>
  <div class="workbench-root">
    <header class="wb-header">
      <div class="wb-title-wrap">
        <h2>统一开发工作台</h2>
        <span class="wb-sub">开发 / 测试 / 发版一体化</span>
      </div>
      <div class="wb-meta">
        <input v-model="platformCode" class="head-input short" placeholder="一级平台，如 douyin" />
        <input v-model="appSlug" class="head-input short" placeholder="应用标识，如 new_app" />
        <input v-model="targetDir" class="head-input short" placeholder="目标目录(可选)，如 douyin/custom" />
        <button class="btn ghost" @click="createScaffold">创建骨架</button>
        <button class="btn ghost" @click="saveCurrentFile" :disabled="!activeTab">保存当前</button>
        <button class="btn ghost" @click="saveAllFiles" :disabled="!openTabs.length">保存全部</button>
      </div>
    </header>

    <section class="wb-main">
      <aside class="wb-explorer">
        <div class="pane-title explorer-title">
          <span>应用目录树</span>
        </div>
        <div class="explorer-toolbar">
          <button class="toolbar-icon-btn" title="根目录新建文件" @click="createFile('')">
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M4 1.75h5.25L13 5.5V14a1.25 1.25 0 0 1-1.25 1.25h-7.5A1.25 1.25 0 0 1 3 14V3A1.25 1.25 0 0 1 4.25 1.75zM9 2.8V5.5h2.7" />
              <path d="M8 8v4M6 10h4" />
            </svg>
          </button>
          <button class="toolbar-icon-btn" title="根目录新建目录" @click="createDirectory('')">
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M1.75 4A1.25 1.25 0 0 1 3 2.75h3l1.1 1.1h5.9A1.25 1.25 0 0 1 14.25 5v7A1.25 1.25 0 0 1 13 13.25H3A1.25 1.25 0 0 1 1.75 12z" />
              <path d="M8 7.5v4M6 9.5h4" />
            </svg>
          </button>
          <button class="toolbar-icon-btn" title="刷新目录" @click="refreshExplorer">
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M13.2 7.2A5.2 5.2 0 1 1 11.8 3M12 1.8v3h-3" />
            </svg>
          </button>
          <button class="toolbar-icon-btn" title="折叠全部目录" @click="collapseAllDirs">
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M2.5 4.25h11M2.5 8h11M2.5 11.75h11" />
              <path d="M4.8 3l-2 2 2 2M4.8 6.8l-2 2 2 2M4.8 10.6l-2 2" />
            </svg>
          </button>
        </div>
        <div class="tree" @contextmenu.prevent="openRootContextMenu($event)">
          <div
            v-for="row in treeRenderRows"
            :key="row.key"
          >
            <div
              v-if="row.kind === 'node' && row.node"
              class="tree-node"
              :class="{ active: activePath === row.node.path, dir: row.node.isDir }"
              :style="{ paddingLeft: `${10 + row.node.depth * 16}px` }"
              @click="handleTreeClick(row.node)"
              @contextmenu.prevent.stop="openContextMenu($event, row.node)"
            >
              <span class="caret">{{ row.node.isDir ? (isExpanded(row.node.path) ? '▾' : '▸') : '' }}</span>
              <span class="node-icon" :class="nodeIconClass(row.node.name, row.node.isDir)"></span>
              <input
                v-if="renameState.path === row.node.path"
                ref="renameInputRef"
                v-model="renameState.nameInput"
                class="tree-inline-input"
                :class="{ 'has-error': !!renameState.errorText }"
                @click.stop
                @keydown.enter.stop.prevent="submitInlineRename"
                @keydown.esc.stop.prevent="cancelInlineRename"
              />
              <div v-if="renameState.path === row.node.path && renameState.errorText" class="tree-inline-error">
                {{ renameState.errorText }}
              </div>
              <span v-else class="node-name">{{ row.node.name }}</span>
            </div>
            <div
              v-else
              class="tree-node creating"
              :style="{ paddingLeft: `${10 + row.depth * 16}px` }"
            >
              <div class="create-inline-row">
                <span class="caret"></span>
                <span class="node-icon" :class="inlineCreate.isDir ? 'folder' : 'py'"></span>
                <input
                  ref="createInputRef"
                  v-model="inlineCreate.nameInput"
                  class="tree-inline-input"
                  :class="{ 'has-error': !!inlineCreate.errorText }"
                  :placeholder="inlineCreate.isDir ? '目录名' : '文件名(.py)'"
                  @keydown.enter.stop.prevent="submitInlineCreate"
                  @keydown.esc.stop.prevent="cancelInlineCreate"
                />
                <button class="inline-text-btn" @click="submitInlineCreate">确定</button>
                <button class="inline-text-btn" @click="cancelInlineCreate">取消</button>
              </div>
              <div v-if="inlineCreate.errorText" class="tree-inline-error">{{ inlineCreate.errorText }}</div>
            </div>
          </div>
          <div v-if="visibleNodes.length === 0 && !inlineCreate.visible" class="tree-empty">先创建骨架后开始开发</div>
        </div>
        <div
          v-if="contextMenu.visible"
          class="tree-context-menu"
          :style="{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }"
          @click.stop
        >
          <button v-if="contextMenu.targetIsDir" class="ctx-item" @click="createFile(contextMenu.targetPath)">新建文件</button>
          <button v-if="contextMenu.targetIsDir" class="ctx-item" @click="createDirectory(contextMenu.targetPath)">新建目录</button>
          <button class="ctx-item" @click="renameNode(contextMenu.targetPath)">重命名</button>
          <button class="ctx-item danger" @click="deleteNode(contextMenu.targetPath)">删除</button>
        </div>
      </aside>

      <main class="wb-editor">
        <div class="tabs">
          <button
            v-for="tab in openTabs"
            :key="tab.path"
            class="tab"
            :class="{ active: tab.path === activePath }"
            @click="activateTab(tab.path)"
          >
            <span class="tab-icon" :class="nodeIconClass(tab.name, false)"></span>
            <span class="tab-name">{{ tab.name }}</span>
            <span v-if="tab.dirty" class="dirty-dot"></span>
            <span class="tab-close" @click.stop="closeTab(tab.path)">×</span>
          </button>
          <div v-if="openTabs.length === 0" class="tabs-empty">未打开文件</div>
        </div>

        <div class="path-bar">
          <span class="path-text">{{ activeTab?.path || '请选择左侧文件' }}</span>
        </div>

        <textarea
          v-if="activeTab"
          v-model="activeCode"
          class="editor"
          spellcheck="false"
          placeholder="在这里编写代码..."
        />
        <div v-else class="editor-empty">请选择左侧文件开始编辑</div>
      </main>

      <aside class="wb-side">
        <div class="pane-title">阶段状态</div>
        <div class="stage-list">
          <div class="stage-item" :class="{ ok: stageStatus.dev }">开发中</div>
          <div class="stage-item" :class="{ ok: stageStatus.tested }">测试通过</div>
          <div class="stage-item" :class="{ ok: stageStatus.releasable }">可发版</div>
          <div class="stage-item" :class="{ ok: stageStatus.released }">已发版</div>
        </div>

        <div class="pane-title top-gap">输入参数 input</div>
        <div class="form-grid">
          <label v-if="false" class="field">
            <span>账号</span>
            
          </label>
          <label v-if="false" class="field">
            <span>密码</span>
            
          </label>
          <label class="field">
            <span>默认下载天数</span>
            <input v-model.number="inputModel.default_download_days" class="field-input" type="number" min="1" />
          </label>
          <label class="field checkbox">
            <input v-model="inputModel.runtime.real_browser" type="checkbox" />
            <span>real_browser</span>
          </label>
          <label class="field full">
            <span>页面参数 page_params (JSON)</span>
            <textarea v-model="pageParamsJson" class="field-textarea" />
          </label>
          <label class="field full">
            <span>account_config (JSON)</span>
            <textarea v-model="accountConfigJson" class="field-textarea" />
          </label>
          <label class="field full">
            <span>存储 storage (JSON)</span>
            <textarea v-model="storageJson" class="field-textarea" />
          </label>
        </div>

        <div class="side-actions">
          <button class="btn primary" @click="runTest">测试运行</button>
        </div>

        <div class="pane-title top-gap">测试结果</div>
        <div class="summary">
          <span>状态：<b :class="runResult?.success ? 'ok-text' : 'warn-text'">{{ runStatusText }}</b></span>
          <span>耗时：{{ runResult?.duration_ms ?? '-' }} ms</span>
          <span>条数：{{ runResult?.rows_count ?? '-' }}</span>
          <span>日期：{{ runResult?.start_date ?? '-' }} ~ {{ runResult?.end_date ?? '-' }}</span>
        </div>
        <div class="logs">
          <div class="log-row" v-for="(log, idx) in runResult?.logs || []" :key="`${idx}-${log.time}`">
            <div class="log-time">{{ log.time }}</div>
            <div class="log-msg">{{ log.message }}</div>
            <pre v-if="log.ext" class="log-ext">{{ jsonText(log.ext) }}</pre>
          </div>
          <div v-if="!runResult || !runResult.logs.length" class="empty-line">暂无日志</div>
        </div>

        <div class="pane-title top-gap">发版面板</div>
        <div class="form-grid">
          <label class="field">
            <span>版本号</span>
            <input v-model="releaseForm.version" class="field-input" placeholder="如 1.0.1" />
          </label>
          <label class="field">
            <span>发布人</span>
            <input v-model="releaseForm.released_by" class="field-input" placeholder="如 kun-kun" />
          </label>
          <label class="field full">
            <span>Checksum</span>
            <input v-model="releaseForm.checksum" class="field-input" />
          </label>
          <label class="field full">
            <span>发布说明</span>
            <textarea v-model="releaseForm.release_notes" class="field-textarea" />
          </label>
        </div>
        <div class="side-actions">
          <button class="btn primary" :disabled="!canRelease" @click="releaseNow">发版</button>
        </div>
      </aside>
    </section>

    <div v-if="actionModal.visible" class="action-modal-mask" @click.self="closeActionModal">
      <div class="action-modal">
        <div class="action-modal-header">
          <h3>{{ actionModalTitle }}</h3>
          <button class="modal-close" @click="closeActionModal">×</button>
        </div>
        <div class="action-modal-body">
          <div class="modal-path">
            目标：{{ (actionModal.type === 'create_dir' || actionModal.type === 'create_file') ? (sanitizeNodeName(actionModal.baseDir) || '/') : (actionModal.targetPath || '-') }}
          </div>

          <label v-if="actionModal.type !== 'delete'" class="field">
            <span>{{ actionModalNameLabel }}</span>
            <input
              v-model="actionModal.nameInput"
              class="field-input"
              :placeholder="actionModalNamePlaceholder"
              @keydown.enter.prevent="submitActionModal"
            />
          </label>

          <label v-if="actionModal.type === 'create_dir' || actionModal.type === 'create_file'" class="field">
            <span>创建位置（相对路径，留空为根目录）</span>
            <input
              v-model="actionModal.baseDir"
              class="field-input"
              placeholder="例如 collect_instructions/douyin"
              @keydown.enter.prevent="submitActionModal"
            />
          </label>

          <div v-if="actionModal.type === 'delete'" class="delete-check-box">
            <div v-if="actionModal.loading" class="delete-check-item">正在检查关联状态...</div>
            <div v-else-if="actionModal.deleteCheck" class="delete-check-list">
              <div class="delete-check-item">已发版：{{ actionModal.deleteCheck.released_count }}</div>
              <div class="delete-check-item">已上架：{{ actionModal.deleteCheck.listed_count }}</div>
              <div class="delete-check-item">已连接任务：{{ actionModal.deleteCheck.task_count }}</div>
              <div class="delete-check-item">
                关联适配器：{{ actionModal.deleteCheck.adapter_keys.length ? actionModal.deleteCheck.adapter_keys.join('，') : '无' }}
              </div>
              <div
                class="delete-check-tip"
                :class="actionModal.deleteCheck.can_delete ? 'ok' : 'danger'"
              >
                {{ actionModal.deleteCheck.can_delete ? '可删除：未发现上架或任务连接。' : '不可删除：存在上架或连接任务，请先处理关联关系。' }}
              </div>
            </div>
            <div v-else class="delete-check-item">未获取到删除检查结果</div>
          </div>

          <div v-if="actionModal.errorText" class="modal-error">{{ actionModal.errorText }}</div>
        </div>
        <div class="action-modal-footer">
          <button class="btn ghost" :disabled="actionModal.submitting" @click="closeActionModal">取消</button>
          <button
            class="btn"
            :class="actionModal.type === 'delete' ? 'danger-fill' : 'primary'"
            :disabled="actionConfirmDisabled"
            @click="submitActionModal"
          >
            {{ actionModal.submitting ? '处理中...' : actionModalConfirmText }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 统一工作台核心逻辑。
 * 职责：
 * 1. 维护目录树与多标签文件编辑状态。
 * 2. 维护统一 input 对象并触发测试运行。
 * 3. 基于测试快照控制发版门禁，测试通过后才允许发布。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { useMessage } from 'naive-ui'

interface TreeNode {
  name: string
  path: string
  isDir: boolean
  depth: number
}

interface TreeBuilderNode {
  name: string
  path: string
  isDir: boolean
  depth: number
  children: Map<string, TreeBuilderNode>
}

interface OpenTab {
  name: string
  path: string
  code: string
  dirty: boolean
}

interface InstructionRow {
  relative_path: string
  is_dir?: boolean
}

interface RunLog {
  time: string
  message: string
  ext?: Record<string, unknown>
}

interface RunResult {
  success: boolean
  rows_count: number
  duration_ms: number
  start_date: string
  end_date: string
  logs: RunLog[]
  data_preview: Array<Record<string, unknown>>
  runtime_init?: Record<string, unknown>
  error_message?: string
}

type ActionType = 'create_dir' | 'create_file' | 'rename' | 'delete'

interface DeleteCheckResult {
  can_delete: boolean
  adapter_keys: string[]
  released_count: number
  listed_count: number
  task_count: number
}

interface InlineCreateState {
  visible: boolean
  isDir: boolean
  parentPath: string
  nameInput: string
  errorText: string
}

interface RenameState {
  path: string
  isDir: boolean
  nameInput: string
  errorText: string
}

interface ContextMenuState {
  visible: boolean
  x: number
  y: number
  targetPath: string
  targetIsDir: boolean
}

interface TreeRenderRow {
  kind: 'node' | 'create'
  key: string
  depth: number
  node?: TreeNode
}

const message = useMessage()

const platformCode = ref('douyin')
const appSlug = ref('new_app')
const targetDir = ref('')
const activePath = ref('')
const expandedDirs = ref<Set<string>>(new Set())
const openTabs = ref<OpenTab[]>([])
const runResult = ref<RunResult | null>(null)
const releasedVersion = ref('')
const instructionRows = ref<InstructionRow[]>([])

const inputModel = reactive({
  credentials: { username: '', password: '' },
  page_params: { keyword: '你好' as string },
  account_config: {} as Record<string, unknown>,
  default_download_days: 1,
  runtime: { real_browser: true },
  storage: {
    type: 'mysql',
    db_host: '127.0.0.1',
    db_port: 3306,
    db_user: 'root',
    db_password: '',
    db_name: 'dc_connection',
  },
})

const pageParamsJson = ref(JSON.stringify(inputModel.page_params, null, 2))
const accountConfigJson = ref(JSON.stringify(inputModel.account_config, null, 2))
const storageJson = ref(JSON.stringify(inputModel.storage, null, 2))

const releaseForm = reactive({
  version: '1.0.0',
  released_by: 'kun-kun',
  checksum: '',
  release_notes: '',
})

const actionModal = reactive({
  visible: false,
  type: 'create_dir' as ActionType,
  nameInput: '',
  targetPath: '',
  targetIsDir: false,
  baseDir: '',
  submitting: false,
  loading: false,
  errorText: '',
  deleteCheck: null as DeleteCheckResult | null,
})
const createInputRef = ref<HTMLInputElement | null>(null)
const renameInputRef = ref<HTMLInputElement | null>(null)
const inlineCreate = reactive<InlineCreateState>({
  visible: false,
  isDir: false,
  parentPath: '',
  nameInput: '',
  errorText: '',
})
const renameState = reactive<RenameState>({
  path: '',
  isDir: false,
  nameInput: '',
  errorText: '',
})
const contextMenu = reactive<ContextMenuState>({
  visible: false,
  x: 0,
  y: 0,
  targetPath: '',
  targetIsDir: false,
})

function appAdapterPath(): string {
  const platform = platformCode.value.trim().toLowerCase()
  const slug = appSlug.value.trim().toLowerCase().replace(/-/g, '_')
  return `${platform}/${slug}.py`
}

/**
 * 拉取“已开发指令/适配器”全量文件清单，目录树以真实文件为准，避免误以为文件被删除。
 */
async function loadInstructionRows(): Promise<void> {
  const previousExpanded = new Set(expandedDirs.value)
  const res = await axios.get('/api/v1/dev/instructions')
  instructionRows.value = res.data?.data || []
  const validDirs = new Set<string>()
  const topDirs = new Set<string>()
  for (const row of instructionRows.value) {
    const normalized = String(row.relative_path || '').replace(/\\/g, '/').trim()
    if (!normalized) continue
    const parts = normalized.split('/').filter(Boolean)
    if (!parts.length) continue
    topDirs.add(parts[0])
    let current = ''
    for (let i = 0; i < parts.length - 1; i += 1) {
      current = current ? `${current}/${parts[i]}` : parts[i]
      validDirs.add(current)
    }
    if (row.is_dir) validDirs.add(normalized)
  }
  if (previousExpanded.size > 0) {
    expandedDirs.value = new Set(Array.from(previousExpanded).filter((path) => validDirs.has(path)))
  } else {
    expandedDirs.value = topDirs
  }
}

function hasInstructionRow(path: string, isDir?: boolean): boolean {
  return instructionRows.value.some((row) => {
    if (row.relative_path !== path) return false
    if (typeof isDir === 'boolean') return Boolean(row.is_dir) === isDir
    return true
  })
}

function ensureParentDirRows(path: string): void {
  const parts = path.split('/').filter(Boolean)
  let current = ''
  for (let i = 0; i < parts.length - 1; i += 1) {
    current = current ? `${current}/${parts[i]}` : parts[i]
    if (!hasInstructionRow(current, true)) {
      instructionRows.value.push({ relative_path: current, is_dir: true })
    }
  }
}

function applyCreatedNode(path: string, isDir: boolean): void {
  ensureParentDirRows(path)
  if (!hasInstructionRow(path, isDir)) {
    instructionRows.value.push({ relative_path: path, is_dir: isDir })
  }
}

function applyRenamedNode(oldPath: string, newPath: string, isDir: boolean): void {
  instructionRows.value = instructionRows.value.map((row) => {
    const path = row.relative_path
    if (isDir) {
      if (path === oldPath || path.startsWith(`${oldPath}/`)) {
        return { ...row, relative_path: `${newPath}${path.slice(oldPath.length)}` }
      }
      return row
    }
    if (path === oldPath) return { ...row, relative_path: newPath }
    return row
  })
}

function applyDeletedNode(path: string, isDir: boolean): void {
  instructionRows.value = instructionRows.value.filter((row) => {
    if (isDir) return row.relative_path !== path && !row.relative_path.startsWith(`${path}/`)
    return row.relative_path !== path
  })
}

function remapExpandedAfterRename(oldPath: string, newPath: string, isDir: boolean): void {
  if (!isDir) return
  const next = new Set<string>()
  for (const item of expandedDirs.value) {
    if (item === oldPath || item.startsWith(`${oldPath}/`)) {
      next.add(`${newPath}${item.slice(oldPath.length)}`)
    } else {
      next.add(item)
    }
  }
  expandedDirs.value = next
}

function removeExpandedAfterDelete(path: string, isDir: boolean): void {
  if (!isDir) return
  expandedDirs.value = new Set(
    Array.from(expandedDirs.value).filter((item) => item !== path && !item.startsWith(`${path}/`))
  )
}

function sortTreeNodes(nodes: TreeBuilderNode[]): TreeBuilderNode[] {
  return nodes.sort((a, b) => {
    if (a.isDir !== b.isDir) return a.isDir ? -1 : 1
    return a.name.localeCompare(b.name)
  })
}

function flattenTree(nodes: TreeBuilderNode[], output: TreeNode[]): void {
  for (const node of sortTreeNodes(nodes)) {
    output.push({
      name: node.name,
      path: node.path,
      isDir: node.isDir,
      depth: node.depth,
    })
    flattenTree(Array.from(node.children.values()), output)
  }
}

const treeNodes = computed<TreeNode[]>(() => {
  const roots = new Map<string, TreeBuilderNode>()
  for (const row of instructionRows.value) {
    const path = String(row.relative_path || '').replace(/\\/g, '/').trim()
    if (!path) continue
    const leafIsDir = Boolean(row.is_dir)
    const parts = path.split('/')
    let currentPath = ''
    let currentLevel = roots
    parts.forEach((part, idx) => {
      currentPath = currentPath ? `${currentPath}/${part}` : part
      const isLeaf = idx === parts.length - 1
      const nodeIsDir = !isLeaf || leafIsDir
      const existing = currentLevel.get(part)
      if (existing) {
        if (nodeIsDir) existing.isDir = true
        if (!isLeaf) currentLevel = existing.children
        return
      }
      const created: TreeBuilderNode = {
        name: part,
        path: currentPath,
        isDir: nodeIsDir,
        depth: idx,
        children: new Map<string, TreeBuilderNode>(),
      }
      currentLevel.set(part, created)
      if (!isLeaf) currentLevel = created.children
    })
  }

  const output: TreeNode[] = []
  flattenTree(Array.from(roots.values()), output)
  return output
})

const visibleNodes = computed(() => {
  return treeNodes.value.filter((node) => {
    if (node.depth === 0) return true
    const parents = node.path.split('/').slice(0, -1)
    if (!parents.length) return true
    let current = ''
    for (const segment of parents) {
      current = current ? `${current}/${segment}` : segment
      if (!expandedDirs.value.has(current)) return false
    }
    return true
  })
})

const activeTab = computed(() => openTabs.value.find((t) => t.path === activePath.value) || null)
const activeCode = computed({
  get: () => activeTab.value?.code || '',
  set: (val: string) => {
    const tab = activeTab.value
    if (!tab) return
    tab.code = val
    tab.dirty = true
  },
})

const stageStatus = computed(() => ({
  dev: openTabs.value.length > 0,
  tested: !!runResult.value?.success,
  releasable: !!runResult.value?.success,
  released: !!releasedVersion.value,
}))

const runStatusText = computed(() => {
  if (!runResult.value) return '未运行'
  return runResult.value.success ? '成功' : '失败'
})

const canRelease = computed(() => !!runResult.value?.success)

const actionModalTitle = computed(() => {
  if (actionModal.type === 'create_dir') return '新建目录'
  if (actionModal.type === 'create_file') return '新建文件'
  if (actionModal.type === 'rename') return '重命名'
  return '删除确认'
})

const actionModalNameLabel = computed(() => {
  if (actionModal.type === 'create_dir') return '目录名'
  if (actionModal.type === 'create_file') return '文件名（.py）'
  return '新名称'
})

const actionModalNamePlaceholder = computed(() => {
  if (actionModal.type === 'create_dir') return '例如 douyin'
  if (actionModal.type === 'create_file') return '例如 report_collect.py'
  return '请输入新名称'
})

const actionModalConfirmText = computed(() => {
  if (actionModal.type === 'delete') return '确认删除'
  if (actionModal.type === 'rename') return '确认重命名'
  return '确认'
})

const actionConfirmDisabled = computed(() => {
  if (actionModal.submitting || actionModal.loading) return true
  if (actionModal.type === 'delete') return !actionModal.deleteCheck?.can_delete
  return !sanitizeNodeName(actionModal.nameInput)
})

const treeRenderRows = computed<TreeRenderRow[]>(() => {
  const rows: TreeRenderRow[] = visibleNodes.value.map((node) => ({
    kind: 'node',
    key: `node:${node.path}`,
    depth: node.depth,
    node,
  }))
  if (!inlineCreate.visible) return rows

  const parent = sanitizeNodeName(inlineCreate.parentPath)
  const createDepth = parent ? parent.split('/').filter(Boolean).length : 0
  const parentPrefix = parent ? `${parent}/` : ''
  const isDirectChild = (row: TreeRenderRow): boolean => {
    if (row.kind !== 'node' || !row.node) return false
    return row.node.depth === createDepth && parentDir(row.node.path) === parent
  }

  let startIndex = 0
  let endIndex = rows.length
  if (parent) {
    const parentIndex = rows.findIndex((row) => row.kind === 'node' && row.node?.path === parent)
    if (parentIndex < 0) {
      startIndex = rows.length
      endIndex = rows.length
    } else {
      startIndex = parentIndex + 1
      endIndex = rows.length
      for (let i = startIndex; i < rows.length; i += 1) {
        const candidate = rows[i]
        if (candidate.kind !== 'node' || !candidate.node) continue
        if (!candidate.node.path.startsWith(parentPrefix)) {
          endIndex = i
          break
        }
      }
    }
  }

  let insertIndex = startIndex
  if (inlineCreate.isDir) {
    insertIndex = startIndex
  } else {
    let firstFileIndex = -1
    for (let i = startIndex; i < endIndex; i += 1) {
      const candidate = rows[i]
      if (!isDirectChild(candidate) || !candidate.node) continue
      if (!candidate.node.isDir) {
        firstFileIndex = i
        break
      }
    }
    insertIndex = firstFileIndex >= 0 ? firstFileIndex : endIndex
  }

  rows.splice(insertIndex, 0, {
    kind: 'create',
    key: `create:${parent || '__root__'}`,
    depth: createDepth,
  })
  return rows
})

function isExpanded(path: string): boolean {
  return expandedDirs.value.has(path)
}

function nodeIconClass(name: string, isDir: boolean): string {
  if (isDir) return 'folder'
  if (name.endsWith('.py')) return 'py'
  if (name.endsWith('.json')) return 'json'
  if (name.endsWith('.md')) return 'md'
  return 'file'
}

function activateTab(path: string): void {
  activePath.value = path
}

function closeTab(path: string): void {
  const idx = openTabs.value.findIndex((tab) => tab.path === path)
  if (idx < 0) return
  openTabs.value.splice(idx, 1)
  if (activePath.value !== path) return
  activePath.value = openTabs.value[idx]?.path || openTabs.value[idx - 1]?.path || ''
}

async function readFile(path: string): Promise<string> {
  const res = await axios.get('/api/v1/dev/instructions/content', { params: { relative_path: path } })
  return res.data?.data?.content || ''
}

/**
 * 点击目录树节点：目录执行展开/收起，文件执行打开标签页。
 */
async function handleTreeClick(node: TreeNode): Promise<void> {
  closeContextMenu()
  activePath.value = node.path
  if (node.isDir) {
    targetDir.value = node.path
    const next = new Set(expandedDirs.value)
    if (next.has(node.path)) {
      next.delete(node.path)
      // 收起父目录时同步移除所有子目录展开状态，避免“父目录收起但子文件仍可见”的错位问题。
      for (const expandedPath of Array.from(next)) {
        if (expandedPath.startsWith(`${node.path}/`)) next.delete(expandedPath)
      }
    } else {
      next.add(node.path)
    }
    expandedDirs.value = next
    return
  }

  const exists = openTabs.value.find((tab) => tab.path === node.path)
  if (exists) return

  const code = await readFile(node.path).catch(() => '')
  openTabs.value.push({ name: node.name, path: node.path, code, dirty: false })
}

function findNode(path: string): TreeNode | null {
  return treeNodes.value.find((node) => node.path === path) || null
}

function parentDir(path: string): string {
  const parts = path.split('/').slice(0, -1)
  return parts.join('/')
}

function sanitizeNodeName(name: string): string {
  return name.trim().replace(/\\/g, '/').replace(/^\/+|\/+$/g, '')
}

function duplicateNameError(name: string): string {
  return `此位置已存在文件或文件夹 ${name}。请选择其他名称。`
}

function isApiOk(resp: any): boolean {
  return Number(resp?.data?.code) === 0
}

function apiMessage(resp: any, fallback: string): string {
  return String(resp?.data?.message || fallback)
}

/**
 * 规范化 Python 文件名：
 * 1. 无后缀时自动补齐 .py
 * 2. 存在非 .py 后缀时直接报错
 */
function normalizePythonFileName(rawName: string): { ok: boolean; fileName: string; error?: string } {
  const name = sanitizeNodeName(rawName)
  if (!name || name.includes('/')) return { ok: false, fileName: '', error: '文件名不合法' }
  const lastDot = name.lastIndexOf('.')
  if (lastDot > 0 && !name.endsWith('.py')) {
    return { ok: false, fileName: '', error: '仅支持创建/重命名为 .py 文件，请修改后缀' }
  }
  return { ok: true, fileName: name.endsWith('.py') ? name : `${name}.py` }
}

function resetActionModal(type: ActionType): void {
  actionModal.visible = true
  actionModal.type = type
  actionModal.nameInput = ''
  actionModal.targetPath = ''
  actionModal.targetIsDir = false
  actionModal.baseDir = ''
  actionModal.submitting = false
  actionModal.loading = false
  actionModal.errorText = ''
  actionModal.deleteCheck = null
}

function closeActionModal(): void {
  actionModal.visible = false
  actionModal.submitting = false
  actionModal.loading = false
  actionModal.errorText = ''
}

function closeContextMenu(): void {
  contextMenu.visible = false
}

function openContextMenu(event: MouseEvent, node: TreeNode): void {
  activePath.value = node.path
  contextMenu.visible = true
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.targetPath = node.path
  contextMenu.targetIsDir = node.isDir
}

function openRootContextMenu(event: MouseEvent): void {
  contextMenu.visible = true
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.targetPath = ''
  contextMenu.targetIsDir = true
}

async function refreshExplorer(): Promise<void> {
  await loadInstructionRows()
  message.success('目录已刷新')
}

function collapseAllDirs(): void {
  expandedDirs.value = new Set()
}

function cancelInlineCreate(): void {
  inlineCreate.visible = false
  inlineCreate.nameInput = ''
  inlineCreate.errorText = ''
}

function cancelInlineRename(): void {
  renameState.path = ''
  renameState.nameInput = ''
  renameState.errorText = ''
}

/**
 * 目录树行内新建：贴近 VSCode 的资源管理器交互。
 */
async function createDirectory(parentPath?: string): Promise<void> {
  const parent = sanitizeNodeName(parentPath ?? '')
  closeContextMenu()
  cancelInlineRename()
  inlineCreate.visible = true
  inlineCreate.isDir = true
  inlineCreate.parentPath = parent
  inlineCreate.nameInput = ''
  inlineCreate.errorText = ''
  if (parent) {
    const next = new Set(expandedDirs.value)
    next.add(parent)
    expandedDirs.value = next
  }
  await nextTick()
  createInputRef.value?.focus()
}

async function createFile(parentPath?: string): Promise<void> {
  const parent = sanitizeNodeName(parentPath ?? '')
  closeContextMenu()
  cancelInlineRename()
  inlineCreate.visible = true
  inlineCreate.isDir = false
  inlineCreate.parentPath = parent
  inlineCreate.nameInput = ''
  inlineCreate.errorText = ''
  if (parent) {
    const next = new Set(expandedDirs.value)
    next.add(parent)
    expandedDirs.value = next
  }
  await nextTick()
  createInputRef.value?.focus()
}

async function submitInlineCreate(): Promise<void> {
  inlineCreate.errorText = ''
  const inputName = sanitizeNodeName(inlineCreate.nameInput)
  if (!inputName || inputName.includes('/')) {
    inlineCreate.errorText = inlineCreate.isDir ? '目录名不合法' : '文件名不合法'
    return
  }
  const normalizedFile = inlineCreate.isDir ? null : normalizePythonFileName(inputName)
  if (normalizedFile && !normalizedFile.ok) {
    inlineCreate.errorText = normalizedFile.error || '仅支持 .py 文件'
    return
  }
  const fileOrDirName = inlineCreate.isDir ? inputName : normalizedFile!.fileName
  const parent = sanitizeNodeName(inlineCreate.parentPath)
  const relativePath = parent ? `${parent}/${fileOrDirName}` : fileOrDirName
  const resp = await axios.post('/api/v1/dev/workbench/fs/node', {
    relative_path: relativePath,
    is_dir: inlineCreate.isDir,
    content: inlineCreate.isDir ? undefined : '',
  })
  if (!isApiOk(resp)) {
    if (Number(resp?.data?.code) === 409) {
      inlineCreate.errorText = duplicateNameError(fileOrDirName)
      return
    }
    inlineCreate.errorText = apiMessage(resp, '创建失败，请稍后重试')
    return
  }
  applyCreatedNode(relativePath, inlineCreate.isDir)
  activePath.value = relativePath
  if (!inlineCreate.isDir) {
    const code = await readFile(relativePath).catch(() => '')
    openTabs.value.push({ name: fileOrDirName, path: relativePath, code, dirty: false })
  } else {
    const next = new Set(expandedDirs.value)
    next.add(relativePath)
    expandedDirs.value = next
  }
  cancelInlineCreate()
  message.success(inlineCreate.isDir ? '目录已创建' : '文件已创建')
}

function remapTabsAfterRename(oldPath: string, newPath: string, isDir: boolean): void {
  const mapped = openTabs.value.map((tab) => {
    if (isDir) {
      if (!tab.path.startsWith(`${oldPath}/`)) return tab
      const suffix = tab.path.slice(oldPath.length)
      return { ...tab, path: `${newPath}${suffix}` }
    }
    if (tab.path !== oldPath) return tab
    return { ...tab, path: newPath, name: newPath.split('/').pop() || tab.name }
  })
  openTabs.value = mapped

  if (isDir) {
    if (activePath.value === oldPath || activePath.value.startsWith(`${oldPath}/`)) {
      activePath.value = `${newPath}${activePath.value.slice(oldPath.length)}`
    }
  } else if (activePath.value === oldPath) {
    activePath.value = newPath
  }
}

async function renameNode(targetPath?: string): Promise<void> {
  const path = targetPath || activePath.value
  if (!path) {
    message.warning('请先选中目录或文件')
    return
  }
  const node = findNode(path)
  if (!node) {
    message.warning('未找到选中节点')
    return
  }
  closeContextMenu()
  cancelInlineCreate()
  activePath.value = node.path
  renameState.path = node.path
  renameState.isDir = node.isDir
  renameState.nameInput = node.name
  renameState.errorText = ''
  await nextTick()
  renameInputRef.value?.focus()
}

async function submitInlineRename(): Promise<void> {
  if (!renameState.path) return
  renameState.errorText = ''
  const node = findNode(renameState.path)
  if (!node) {
    cancelInlineRename()
    return
  }
  const nextNameRaw = sanitizeNodeName(renameState.nameInput)
  if (!nextNameRaw || nextNameRaw.includes('/')) {
    renameState.errorText = '名称不合法'
    return
  }
  const normalizedFile = node.isDir ? null : normalizePythonFileName(nextNameRaw)
  if (normalizedFile && !normalizedFile.ok) {
    renameState.errorText = normalizedFile.error || '仅支持 .py 文件'
    return
  }
  const nextName = node.isDir ? nextNameRaw : normalizedFile!.fileName
  const parent = parentDir(node.path)
  const newPath = parent ? `${parent}/${nextName}` : nextName
  if (newPath === node.path) {
    cancelInlineRename()
    return
  }
  const resp = await axios.patch('/api/v1/dev/workbench/fs/node', {
    old_relative_path: node.path,
    new_relative_path: newPath,
  })
  if (!isApiOk(resp)) {
    if (Number(resp?.data?.code) === 409) {
      renameState.errorText = duplicateNameError(nextName)
      return
    }
    renameState.errorText = apiMessage(resp, '重命名失败，请稍后重试')
    return
  }
  remapTabsAfterRename(node.path, newPath, node.isDir)
  applyRenamedNode(node.path, newPath, node.isDir)
  remapExpandedAfterRename(node.path, newPath, node.isDir)
  activePath.value = newPath
  cancelInlineRename()
  message.success('重命名成功')
}

async function deleteNode(targetPath?: string): Promise<void> {
  const path = targetPath || activePath.value
  if (!path) {
    message.warning('请先选中目录或文件')
    return
  }
  const node = findNode(path)
  if (!node) {
    message.warning('未找到选中节点')
    return
  }
  closeContextMenu()
  resetActionModal('delete')
  actionModal.targetPath = node.path
  actionModal.targetIsDir = node.isDir
  actionModal.loading = true
  try {
    const res = await axios.get('/api/v1/dev/workbench/fs/delete-check', {
      params: { relative_path: node.path },
    })
    actionModal.deleteCheck = (res.data?.data || null) as DeleteCheckResult | null
  } catch {
    actionModal.errorText = '删除检查失败，请稍后重试'
  } finally {
    actionModal.loading = false
  }
}

/**
 * 统一提交目录树增删改操作，确保流程一致且可扩展。
 */
async function submitActionModal(): Promise<void> {
  if (actionConfirmDisabled.value) return
  actionModal.submitting = true
  actionModal.errorText = ''
  try {
    if (actionModal.type === 'create_dir') {
      const dirName = sanitizeNodeName(actionModal.nameInput)
      if (!dirName || dirName.includes('/')) throw new Error('目录名不合法')
      const baseDir = sanitizeNodeName(actionModal.baseDir)
      if (baseDir.includes('..')) throw new Error('创建位置不合法')
      const relativePath = baseDir ? `${baseDir}/${dirName}` : dirName
      await axios.post('/api/v1/dev/workbench/fs/node', { relative_path: relativePath, is_dir: true })
      applyCreatedNode(relativePath, true)
      activePath.value = relativePath
      targetDir.value = relativePath
      const next = new Set(expandedDirs.value)
      if (baseDir) next.add(baseDir)
      next.add(relativePath)
      expandedDirs.value = next
      message.success('目录已创建')
      closeActionModal()
      return
    }

    if (actionModal.type === 'create_file') {
      const inputName = sanitizeNodeName(actionModal.nameInput)
      if (!inputName || inputName.includes('/')) throw new Error('文件名不合法')
      const baseDir = sanitizeNodeName(actionModal.baseDir)
      if (baseDir.includes('..')) throw new Error('创建位置不合法')
      const normalizedFile = normalizePythonFileName(inputName)
      if (!normalizedFile.ok) throw new Error(normalizedFile.error || '仅支持 .py 文件')
      const fileName = normalizedFile.fileName
      const relativePath = baseDir ? `${baseDir}/${fileName}` : fileName
      await axios.post('/api/v1/dev/workbench/fs/node', { relative_path: relativePath, is_dir: false, content: '' })
      applyCreatedNode(relativePath, false)
      const code = await readFile(relativePath).catch(() => '')
      openTabs.value.push({ name: fileName, path: relativePath, code, dirty: false })
      activePath.value = relativePath
      if (baseDir) {
        const next = new Set(expandedDirs.value)
        next.add(baseDir)
        expandedDirs.value = next
      }
      message.success('文件已创建')
      closeActionModal()
      return
    }

    if (actionModal.type === 'rename') {
      const node = findNode(actionModal.targetPath)
      if (!node) throw new Error('未找到选中节点')
      const nextNameRaw = sanitizeNodeName(actionModal.nameInput)
      if (!nextNameRaw || nextNameRaw.includes('/')) throw new Error('名称不合法')
      const normalizedFile = node.isDir ? null : normalizePythonFileName(nextNameRaw)
      if (normalizedFile && !normalizedFile.ok) throw new Error(normalizedFile.error || '仅支持 .py 文件')
      const nextName = node.isDir ? nextNameRaw : normalizedFile!.fileName
      const parent = parentDir(node.path)
      const newPath = parent ? `${parent}/${nextName}` : nextName
      if (newPath === node.path) {
        closeActionModal()
        return
      }
      await axios.patch('/api/v1/dev/workbench/fs/node', {
        old_relative_path: node.path,
        new_relative_path: newPath,
      })
      remapTabsAfterRename(node.path, newPath, node.isDir)
      applyRenamedNode(node.path, newPath, node.isDir)
      remapExpandedAfterRename(node.path, newPath, node.isDir)
      activePath.value = newPath
      message.success('重命名成功')
      closeActionModal()
      return
    }

    if (!actionModal.deleteCheck?.can_delete) throw new Error('当前节点存在上架或任务连接，禁止删除')
    await axios.delete('/api/v1/dev/workbench/fs/node', {
      params: { relative_path: actionModal.targetPath },
    })
    if (actionModal.targetIsDir) {
      openTabs.value = openTabs.value.filter((tab) => !tab.path.startsWith(`${actionModal.targetPath}/`))
    } else {
      openTabs.value = openTabs.value.filter((tab) => tab.path !== actionModal.targetPath)
    }
    applyDeletedNode(actionModal.targetPath, actionModal.targetIsDir)
    removeExpandedAfterDelete(actionModal.targetPath, actionModal.targetIsDir)
    activePath.value = ''
    message.success('删除成功')
    closeActionModal()
  } catch (error: unknown) {
    const text = error instanceof Error ? error.message : '操作失败'
    actionModal.errorText = text
    message.error(text)
  } finally {
    actionModal.submitting = false
  }
}

async function saveFile(path: string, content: string): Promise<void> {
  await axios.put('/api/v1/dev/workbench/file', {
    relative_path: path,
    content,
  })
}

async function saveCurrentFile(): Promise<void> {
  const tab = activeTab.value
  if (!tab) {
    message.warning('当前没有打开文件')
    return
  }
  await saveFile(tab.path, tab.code)
  tab.dirty = false
  message.success('当前文件已保存')
}

async function saveAllFiles(): Promise<void> {
  for (const tab of openTabs.value) {
    if (!tab.dirty) continue
    await saveFile(tab.path, tab.code)
    tab.dirty = false
  }
  message.success('文件已全部保存')
}

function schemaTemplate(platform: string, slug: string): string {
  return `"""
输入输出 schema：${platform}/${slug}
用途：
1. 定义 input/output 结构，统一参数读取入口。
"""

from __future__ import annotations
from typing import Any


def build_input(credentials: dict[str, Any], app_params: dict[str, Any]) -> dict[str, Any]:
    """构建统一 input 对象。"""
    input_obj = dict(app_params.get("input") or {})
    if input_obj:
        return input_obj
    return {
        "credentials": credentials,
        "page_params": dict(app_params.get("page_params") or {}),
        "account_config": dict(app_params.get("account_config") or {}),
        "default_download_days": int(app_params.get("default_download_days") or 1),
        "runtime": {
            "real_browser": bool(app_params.get("real_browser", True)),
        },
        "storage": dict(app_params.get("storage") or {}),
    }
`
}

function testsTemplate(platform: string, slug: string): string {
  return `"""
工作台应用最小测试：${platform}/${slug}
用途：
1. 验证应用文件可导入。
"""

from __future__ import annotations

import importlib


def test_import_app_main() -> None:
    """最小可用性测试。"""
    module_name = "infrastructure.connectors.${platform}.${slug}"
    mod = importlib.import_module(module_name)
    assert mod is not None
`
}

/**
 * 创建应用骨架，并补齐 schema/tests 两个规范文件。
 */
async function createScaffold(): Promise<void> {
  const platform = platformCode.value.trim().toLowerCase()
  const slug = appSlug.value.trim().toLowerCase().replace(/-/g, '_')
  if (!platform || !slug) {
    message.warning('请先填写一级平台和应用标识')
    return
  }

  const res = await axios.post('/api/v1/dev/workbench/apps/create', {
    platform_code: platform,
    app_slug: slug,
    target_dir: targetDir.value.trim() || null,
    overwrite: false,
  })
  const createdFiles: string[] = res.data?.data?.files
    ?.filter((item: { relative_path: string; created: boolean }) => item.created)
    ?.map((item: { relative_path: string }) => item.relative_path) || []
  const schemaPath = createdFiles.find((path) => path.startsWith('schema/') && path.endsWith(`/${slug}_schema.py`))
  const testPath = createdFiles.find((path) => path.startsWith('tests/') && path.endsWith(`/test_${slug}.py`))
  if (schemaPath) await saveFile(schemaPath, schemaTemplate(platform, slug))
  if (testPath) await saveFile(testPath, testsTemplate(platform, slug))

  await loadInstructionRows()
  const nextExpanded = new Set(expandedDirs.value)
  for (const path of createdFiles) {
    const parts = path.split('/').slice(0, -1)
    let cursor = ''
    for (const part of parts) {
      cursor = cursor ? `${cursor}/${part}` : part
      nextExpanded.add(cursor)
    }
  }
  expandedDirs.value = nextExpanded
  message.success('应用骨架已生成')
}

function syncInputJson(): boolean {
  try {
    inputModel.page_params = JSON.parse(pageParamsJson.value || '{}')
    inputModel.account_config = JSON.parse(accountConfigJson.value || '{}')
    inputModel.storage = JSON.parse(storageJson.value || '{}')
    inputModel.default_download_days = Math.max(Number(inputModel.default_download_days || 1), 1)
    return true
  } catch {
    message.error('page_params / account_config / storage 不是合法 JSON')
    return false
  }
}

/**
 * 使用统一 input 模型触发测试运行。
 */
async function runTest(): Promise<void> {
  if (!syncInputJson()) return
  await saveAllFiles()
  const relativePath = activePath.value.endsWith('.py') ? activePath.value : appAdapterPath()
  const input = {
    page_params: inputModel.page_params,
    account_config: inputModel.account_config,
    default_download_days: inputModel.default_download_days,
    runtime: inputModel.runtime,
    storage: inputModel.storage,
  }

  const res = await axios.post('/api/v1/dev/workbench/run', {
    relative_path: relativePath,
    credentials: {},
    app_params: {
      ...inputModel.page_params,
      default_download_days: inputModel.default_download_days,
      real_browser: inputModel.runtime.real_browser,
      storage: inputModel.storage,
      input,
    },
    extra: {
      company_name: 'dc_connection',
      platform_code: platformCode.value,
      account_name: 'workbench',
    },
  })
  runResult.value = res.data?.data || null
  if (runResult.value?.success) message.success('测试通过，可发版')
  else message.error(runResult.value?.error_message || '测试失败')
}

function jsonText(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2)
}

/**
 * 触发发版：严格携带 test_snapshot，后端二次校验 success=true。
 */
async function releaseNow(): Promise<void> {
  if (!runResult.value?.success) {
    message.warning('请先测试通过再发版')
    return
  }
  const adapterKey = `${platformCode.value.trim().toLowerCase()}.${appSlug.value.trim().toLowerCase().replace(/-/g, '_')}`
  await axios.post('/api/v1/apps/releases', {
    adapter_key: adapterKey,
    version: releaseForm.version.trim(),
    status: 'released',
    qa_passed: true,
    checksum: releaseForm.checksum.trim() || null,
    release_notes: releaseForm.release_notes.trim() || null,
    released_by: releaseForm.released_by.trim() || null,
    test_snapshot: {
      success: runResult.value.success,
      rows_count: runResult.value.rows_count,
      duration_ms: runResult.value.duration_ms,
      start_date: runResult.value.start_date,
      end_date: runResult.value.end_date,
      timestamp: new Date().toISOString(),
    },
  })
  releasedVersion.value = releaseForm.version
  message.success(`发版完成：${releaseForm.version}`)
}

function handleGlobalClick(): void {
  closeContextMenu()
}

onMounted(() => {
  window.addEventListener('click', handleGlobalClick)
  loadInstructionRows().catch(() => {
    message.error('加载开发文件列表失败')
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('click', handleGlobalClick)
})
</script>

<style scoped>
.workbench-root { display: flex; flex-direction: column; gap: 12px; }
.wb-header {
  display: flex; justify-content: space-between; align-items: center; gap: 12px;
  background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 10px; padding: 10px 12px;
}
.wb-title-wrap h2 { margin: 0; font-size: 20px; color: var(--text-primary); }
.wb-sub { font-size: 12px; color: var(--text-tertiary); }
.wb-meta { display: flex; align-items: center; gap: 8px; }
.head-input { border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; background: var(--bg-base); color: var(--text-primary); }
.head-input.short { width: 220px; }

.wb-main { display: grid; grid-template-columns: 280px 1fr 420px; gap: 12px; }
.wb-explorer, .wb-editor, .wb-side {
  background: var(--bg-card); border: 1px solid var(--border-light); border-radius: 10px; overflow: hidden;
}
.wb-explorer { position: relative; }
.pane-title { padding: 10px 12px; border-bottom: 1px solid var(--border-light); font-size: 13px; color: var(--text-secondary); font-weight: 600; }
.explorer-title { display: flex; justify-content: space-between; align-items: center; }
.explorer-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px dashed var(--border-light);
}
.toolbar-icon-btn {
  width: 28px;
  height: 28px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-subtle);
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.toolbar-icon-btn:hover {
  border-color: var(--accent-copper);
  color: var(--text-primary);
  background: var(--accent-copper-bg);
}
.toolbar-icon-btn svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.35;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.top-gap { margin-top: 8px; border-top: 1px dashed var(--border-light); }

.tree { max-height: calc(100vh - 230px); overflow: auto; padding: 6px 0; }
.tree-node { display: flex; align-items: center; gap: 7px; min-height: 30px; padding-right: 10px; cursor: pointer; color: var(--text-secondary); }
.tree-node:hover { background: var(--select-option-hover); }
.tree-node.active { background: var(--accent-copper-bg); color: var(--text-primary); }
.tree-node.creating {
  display: block;
  background: var(--accent-copper-bg);
  padding-top: 6px;
  padding-bottom: 6px;
}
.create-inline-row {
  display: flex;
  align-items: center;
  gap: 7px;
}
.caret { width: 12px; text-align: center; color: var(--text-tertiary); }
.node-icon { width: 12px; height: 12px; border-radius: 3px; background: #8ea4c0; }
.node-icon.folder { background: #bb955f; }
.node-icon.py { background: linear-gradient(135deg, #3776ab 0 52%, #ffd343 52% 100%); }
.node-icon.json { background: #56b9ff; }
.node-icon.md { background: #a58df6; }
.tree-inline-input {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #fffdf9;
  color: var(--text-primary);
  padding: 4px 6px;
  font-size: 12px;
}
.tree-inline-input.has-error {
  border-color: #d85b54;
  background: #fff4f3;
}
.tree-inline-error {
  margin-left: 20px;
  margin-top: 6px;
  color: #c84a45;
  font-size: 12px;
  line-height: 1.35;
  max-width: 240px;
}
.inline-text-btn {
  border: 1px solid var(--border);
  background: var(--bg-subtle);
  color: var(--text-secondary);
  border-radius: 6px;
  min-width: 44px;
  height: 26px;
  padding: 0 8px;
  font-size: 12px;
  cursor: pointer;
}
.inline-text-btn:hover {
  border-color: var(--accent-copper);
  color: var(--text-primary);
}
.node-action-btn {
  border: 1px solid var(--border);
  background: var(--bg-subtle);
  color: var(--text-secondary);
  border-radius: 5px;
  min-width: 24px;
  height: 22px;
  font-size: 12px;
  cursor: pointer;
}
.node-action-btn.danger { border-color: #c67a64; color: #a44f36; }
.tree-context-menu {
  position: fixed;
  min-width: 138px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: var(--bg-card);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.18);
  padding: 4px;
  z-index: 110;
}
.ctx-item {
  width: 100%;
  border: none;
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  border-radius: 6px;
  padding: 7px 8px;
  cursor: pointer;
  font-size: 12px;
}
.ctx-item:hover { background: var(--select-option-hover); }
.ctx-item.danger { color: #a44f36; }
.tree-empty { padding: 14px; font-size: 12px; color: var(--text-tertiary); }

.tabs { display: flex; align-items: center; gap: 6px; overflow-x: auto; border-bottom: 1px solid var(--border-light); padding: 8px 10px; }
.tab { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--border); background: var(--bg-subtle); color: var(--text-secondary); border-radius: 8px; padding: 5px 8px; cursor: pointer; }
.tab.active { border-color: var(--accent-copper); background: var(--accent-copper-bg); color: var(--text-primary); }
.tab-icon { width: 10px; height: 10px; border-radius: 2px; background: #8ea4c0; }
.tab-icon.py { background: linear-gradient(135deg, #3776ab 0 52%, #ffd343 52% 100%); }
.tab-icon.json { background: #56b9ff; }
.tab-icon.md { background: #a58df6; }
.tab-name { max-width: 180px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.tab-close { width: 16px; height: 16px; display: inline-flex; align-items: center; justify-content: center; border-radius: 4px; }
.tab-close:hover { background: rgba(0, 0, 0, 0.08); }
.dirty-dot { width: 6px; height: 6px; border-radius: 50%; background: #db8745; }
.tabs-empty { color: var(--text-tertiary); font-size: 12px; padding: 2px 0; }

.path-bar { padding: 8px 12px; border-bottom: 1px dashed var(--border-light); }
.path-text { font-size: 12px; color: var(--text-tertiary); font-family: var(--font-mono); }
.editor { width: calc(100% - 24px); margin: 10px 12px 12px; min-height: calc(100vh - 310px); border: 1px solid var(--border-light); border-radius: 8px; padding: 10px; font-family: var(--font-mono); resize: none; background: #fffdf9; color: #2d2a26; }
.editor-empty { padding: 14px; color: var(--text-tertiary); font-size: 12px; }

.wb-side { padding-bottom: 10px; overflow: auto; max-height: calc(100vh - 170px); }
.stage-list { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 10px 12px; }
.stage-item { border: 1px solid var(--border); border-radius: 8px; padding: 8px; text-align: center; color: var(--text-tertiary); background: var(--bg-subtle); font-size: 12px; }
.stage-item.ok { color: #2b8a3e; border-color: #8fd0a0; background: #edf9f0; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 10px 12px; }
.field { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--text-secondary); }
.field.full { grid-column: 1 / -1; }
.field-input, .field-textarea { border: 1px solid var(--border); border-radius: 8px; background: var(--bg-base); color: var(--text-primary); padding: 7px 9px; }
.field-textarea { min-height: 70px; font-family: var(--font-mono); }
.field.checkbox { flex-direction: row; align-items: center; gap: 8px; padding-top: 20px; }

.side-actions { padding: 0 12px 8px; }
.btn { border-radius: 8px; padding: 8px 12px; cursor: pointer; }
.btn.ghost { border: 1px solid var(--border); background: var(--bg-subtle); color: var(--text-secondary); }
.btn.primary { border: 1px solid var(--accent-copper); background: linear-gradient(135deg, var(--accent-copper), #b88560); color: var(--text-inverse); }
.btn.mini { padding: 5px 8px; font-size: 12px; }
.btn.danger { border-color: #c67a64; color: #a44f36; }
.btn.danger-fill { border: 1px solid #bf6d53; background: linear-gradient(135deg, #d27d62, #bf6d53); color: #fff; }
.btn:disabled { opacity: 0.45; cursor: not-allowed; }

.action-modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(18, 16, 12, 0.52);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 90;
}
.action-modal {
  width: min(620px, calc(100vw - 40px));
  border-radius: 12px;
  border: 1px solid var(--border-light);
  background: var(--bg-card);
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.2);
}
.action-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-light);
  padding: 12px 14px;
}
.action-modal-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
}
.modal-close {
  border: 1px solid var(--border);
  background: var(--bg-subtle);
  color: var(--text-secondary);
  width: 28px;
  height: 28px;
  border-radius: 7px;
  cursor: pointer;
}
.action-modal-body { padding: 12px 14px; display: grid; gap: 10px; }
.modal-path { font-size: 12px; color: var(--text-tertiary); font-family: var(--font-mono); }
.delete-check-box {
  border: 1px solid var(--border-light);
  border-radius: 8px;
  background: #faf8f4;
  padding: 10px;
}
.delete-check-list { display: grid; gap: 6px; }
.delete-check-item { font-size: 12px; color: var(--text-secondary); }
.delete-check-tip { margin-top: 4px; font-size: 12px; font-weight: 600; }
.delete-check-tip.ok { color: #2b8a3e; }
.delete-check-tip.danger { color: #b45e3b; }
.modal-error { color: #b45e3b; font-size: 12px; }
.action-modal-footer {
  padding: 0 14px 14px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.summary { padding: 8px 12px; display: grid; gap: 6px; font-size: 12px; color: var(--text-secondary); }
.ok-text { color: #2b8a3e; }
.warn-text { color: #b45e3b; }
.logs { padding: 0 12px 8px; max-height: 220px; overflow: auto; }
.log-row { border-top: 1px solid var(--border-light); padding: 7px 0; }
.log-time { font-size: 11px; color: var(--text-tertiary); font-family: var(--font-mono); }
.log-msg { font-size: 12px; color: var(--text-primary); margin-top: 3px; }
.log-ext { margin: 6px 0 0; padding: 6px; border-radius: 6px; border: 1px solid var(--border-light); background: #faf8f4; font-size: 11px; color: var(--text-secondary); max-height: 90px; overflow: auto; font-family: var(--font-mono); }
.empty-line { padding: 8px 0; color: var(--text-tertiary); font-size: 12px; }

@media (max-width: 1440px) {
  .wb-main { grid-template-columns: 260px 1fr 380px; }
}
@media (max-width: 1200px) {
  .wb-main { grid-template-columns: 1fr; }
  .editor { min-height: 360px; }
  .wb-side { max-height: none; }
}
</style>
