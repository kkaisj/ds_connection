<!--
  连接任务页面
  用途：
  1. 查看任务列表并执行启停、手动执行、删除。
  2. 通过右侧抽屉维护参数配置、存储配置、触发配置、执行日志。
-->
<template>
  <div class="tasks-page">
    <div class="toolbar">
      <div class="view-tabs">
        <button
          v-for="v in views"
          :key="v.key"
          class="view-tab"
          :class="{ active: activeView === v.key }"
          @click="activeView = v.key"
        >
          {{ v.label }}
        </button>
      </div>
      <div class="filter-group">
        <input
          v-model="keyword"
          class="search-input"
          placeholder="搜索任务/应用/店铺"
          @input="debouncedLoad"
        />
        <DcSelect v-model="filterStatus" :options="statusOptions" @change="loadTasks" />
      </div>
    </div>

    <div v-if="activeView === 'list'" class="task-board">
      <div v-if="pagedTasks.length > 0" class="task-grid">
        <article v-for="task in pagedTasks" :key="task.id" class="task-card">
          <div class="task-card-head">
            <div class="task-title-wrap">
              <h3 class="task-title" :title="task.name">{{ task.name }}</h3>
              <span class="task-sub">{{ task.app_name }}</span>
            </div>
            <span class="task-run-badge" :class="`run-${toUiRunStatus(task.last_run_status)}`">
              {{ runStatusLabel(task.last_run_status) }}
            </span>
          </div>

          <div class="task-meta">
            <div class="meta-row">
              <span class="meta-label">平台</span>
              <span class="meta-value">{{ task.platform_name }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">店铺</span>
              <span class="meta-value">{{ task.shop_name }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">调度</span>
              <span class="meta-value mono">{{ task.cron_expr }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">任务状态</span>
              <span class="meta-value">{{ task.status === 'enabled' ? '已启用' : '已暂停' }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">最近执行</span>
              <span class="meta-value">{{ task.last_run_at ? formatTime(task.last_run_at) : '--' }}</span>
            </div>
          </div>

          <div class="task-actions">
            <button class="action-btn" @click="openDrawer(task)">配置</button>
            <button class="action-btn" @click="toggleStatus(task)">
              {{ task.status === 'enabled' ? '暂停' : '启用' }}
            </button>
            <button class="action-btn action-primary" @click="manualRun(task.id)">执行</button>
            <button class="action-btn action-danger" @click="deleteTask(task.id, task.name)">删除</button>
          </div>
        </article>
      </div>
      <div v-else class="card card-padding">
        <div class="empty-cell">暂无匹配任务</div>
      </div>

      <div v-if="totalPages > 1" class="pagination">
        <button class="page-btn" :disabled="page === 1" @click="page--">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button class="page-btn" :disabled="page === totalPages" @click="page++">下一页</button>
      </div>
    </div>

    <div v-if="activeView !== 'list'" class="card card-padding">
      <div class="empty-cell">当前视图沿用列表数据，可先在列表视图完成配置。</div>
    </div>

    <DcConfirm
      v-model:show="showDeleteConfirm"
      title="确认删除任务"
      :desc="`确定要删除任务「${deleteTaskName}」吗？`"
      confirm-text="删除"
      :danger="true"
      @confirm="doDeleteTask"
    />

    <div v-if="drawerVisible" class="drawer-mask" @click.self="closeDrawer">
      <aside class="drawer">
        <div class="drawer-header">
          <div class="drawer-title">任务配置：{{ selectedTask?.name }}</div>
          <button class="close-btn" @click="closeDrawer">×</button>
        </div>

        <div class="drawer-tabs">
          <button
            v-for="tab in drawerTabs"
            :key="tab.key"
            class="tab-btn"
            :class="{ active: activeTab === tab.key }"
            @click="switchTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="drawer-content">
          <section v-if="activeTab === 'params'" class="panel">
            <div class="form-row">
              <label>默认下载天数</label>
              <input v-model.number="paramsDraft.default_download_days" class="input" type="number" min="1" />
            </div>
            <div class="form-row">
              <label>换算日期范围（自动）</label>
              <input :value="dateRangePreview.start_date" class="input" readonly />
              <input :value="dateRangePreview.end_date" class="input mt8" readonly />
            </div>
            <div class="form-row">
              <label>页面参数（JSON）</label>
              <textarea
                v-model="paramsDraft.extra_json"
                class="textarea"
                placeholder='{"page_size": 50, "view": "商品视角"}'
              />
            </div>
            <button class="save-btn" @click="saveParams">保存参数</button>
          </section>

          <section v-if="activeTab === 'storage'" class="panel">
            <div class="form-row">
              <label>存储配置</label>
              <DcSelect v-model="storageDraftId" :options="storageOptions" />
            </div>
            <button class="save-btn" @click="saveStorage">保存存储配置</button>
          </section>

          <section v-if="activeTab === 'trigger'" class="panel">
            <div class="form-row">
              <label>Cron</label>
              <input v-model="triggerDraft.cron_expr" class="input" />
            </div>
            <div class="form-row">
              <label>状态</label>
              <DcSelect v-model="triggerDraft.status" :options="statusOptionsWithValue" />
            </div>
            <button class="save-btn" @click="saveTrigger">保存触发配置</button>
          </section>

          <section v-if="activeTab === 'logs'" class="panel">
            <div class="log-toolbar">
              <label class="log-toolbar-label">执行记录：</label>
              <DcSelect
                v-model="selectedRunId"
                class="run-select"
                :options="runOptions"
                placeholder="请选择执行记录"
                @change="handleRunChange"
              />
              <input
                v-model="logKeyword"
                class="search-input log-search"
                placeholder="搜索日志内容..."
              />
              <button class="action-btn" @click="loadRunsForTask">刷新</button>
            </div>
            <div class="log-table-wrap">
              <table class="log-table">
                <thead>
                  <tr>
                    <th class="time-col">时间</th>
                    <th>内容</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(log, idx) in filteredRunLogs" :key="`${idx}-${log.ts}`">
                    <td class="mono">{{ log.ts ? formatTime(log.ts) : '--' }}</td>
                    <td>
                      <span class="log-level">{{ log.level }}</span>
                      <span class="log-message">{{ log.step }} - {{ log.message }}</span>
                    </td>
                  </tr>
                  <tr v-if="filteredRunLogs.length === 0">
                    <td colspan="2" class="empty-cell">暂无日志</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 任务侧边栏配置逻辑
 * 核心职责：
 * 1. 每个任务独立编辑参数/存储/触发配置。
 * 2. 参数保存使用 default_download_days，并自动换算 start/end 预览。
 * 3. 日志页默认展示最近一次执行，并支持切换执行批次与关键词过滤。
 */
import { computed, onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'
import DcSelect from '@/components/DcSelect.vue'
import DcConfirm from '@/components/DcConfirm.vue'

interface TaskItem {
  id: number
  name: string
  app_id: number
  account_id: number
  storage_config_id: number
  notification_config_id: number
  app_name: string
  platform_code: string
  platform_name: string
  shop_name: string
  cron_expr: string
  status: 'enabled' | 'paused' | string
  params: Record<string, unknown> | null
  last_run_at: string | null
  last_run_status: string | null
}

interface StorageOptionItem {
  id: number
  name: string
  type: string
  status: string
}

interface RunItem {
  id: number
  status: string
  started_at: string | null
}

interface RunLogItem {
  step: string
  level: string
  message: string
  ts: string | null
}

const message = useMessage()

const views = [
  { key: 'list', label: '列表' },
  { key: 'platform', label: '平台' },
  { key: 'account', label: '账号' },
]
const activeView = ref('list')

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'enabled', label: '已启用' },
  { value: 'paused', label: '已暂停' },
]
const statusOptionsWithValue = [
  { value: 'enabled', label: '已启用' },
  { value: 'paused', label: '已暂停' },
]

const tasks = ref<TaskItem[]>([])
const keyword = ref('')
const filterStatus = ref('')
const page = ref(1)
const pageSize = 10

const totalPages = computed(() => Math.max(1, Math.ceil(tasks.value.length / pageSize)))
const pagedTasks = computed(() => {
  const start = (page.value - 1) * pageSize
  return tasks.value.slice(start, start + pageSize)
})

const showDeleteConfirm = ref(false)
const deleteTargetId = ref<number | null>(null)
const deleteTaskName = ref('')

const drawerVisible = ref(false)
const selectedTask = ref<TaskItem | null>(null)
const activeTab = ref<'params' | 'storage' | 'trigger' | 'logs'>('params')
const drawerTabs = [
  { key: 'params', label: '参数配置' },
  { key: 'storage', label: '存储配置' },
  { key: 'trigger', label: '触发配置' },
  { key: 'logs', label: '执行日志' },
] as const

const paramsDraft = ref({
  default_download_days: 1,
  extra_json: '{}',
})
const storageOptions = ref<Array<{ value: number; label: string }>>([])
const storageDraftId = ref<number>(0)
const triggerDraft = ref({
  cron_expr: '',
  status: 'enabled',
})

const runList = ref<RunItem[]>([])
const selectedRunId = ref<number>(0)
const runLogs = ref<RunLogItem[]>([])
const logKeyword = ref('')

const runStatusText: Record<string, string> = {
  success: '完成',
  failed: '失败',
  running: '运行中',
  pending: '等待中',
  cancelled: '已取消',
}

const runOptions = computed(() => {
  const total = runList.value.length
  return runList.value.map((run, index) => {
    const statusText = runStatusText[run.status] || run.status
    const started = run.started_at ? formatTime(run.started_at).substring(0, 16) : '--'
    return {
      value: run.id,
      label: `${total - index}  ${started} (${statusText})`,
    }
  })
})

const filteredRunLogs = computed(() => {
  const kw = logKeyword.value.trim().toLowerCase()
  if (!kw) return runLogs.value
  return runLogs.value.filter((log) => {
    const text = `${log.level} ${log.step} ${log.message}`.toLowerCase()
    return text.includes(kw)
  })
})

function toUiRunStatus(status: string | null | undefined): 'success' | 'running' | 'failed' | 'idle' {
  if (status === 'success') return 'success'
  if (status === 'running' || status === 'pending') return 'running'
  if (status === 'failed' || status === 'cancelled') return 'failed'
  return 'idle'
}

function runStatusLabel(status: string | null | undefined): string {
  const uiStatus = toUiRunStatus(status)
  if (uiStatus === 'success') return '完成'
  if (uiStatus === 'running') return '运行中'
  if (uiStatus === 'failed') return '失败'
  return '未执行'
}

function formatTime(iso: string) {
  return iso.replace('T', ' ').substring(0, 19)
}

async function loadTasks() {
  const params: Record<string, string> = {}
  if (keyword.value) params.keyword = keyword.value
  if (filterStatus.value) params.status = filterStatus.value
  const res = await axios.get('/api/v1/tasks', { params })
  tasks.value = res.data.data || []
  page.value = 1
}

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadTasks, 250)
}

async function toggleStatus(task: TaskItem) {
  const newStatus = task.status === 'enabled' ? 'paused' : 'enabled'
  await axios.patch(`/api/v1/tasks/${task.id}`, { status: newStatus })
  task.status = newStatus
  message.success(newStatus === 'enabled' ? '任务已启用' : '任务已暂停')
}

async function manualRun(taskId: number) {
  await axios.post(`/api/v1/tasks/${taskId}/run`)
  message.success('任务已触发执行')
}

function deleteTask(taskId: number, taskName: string) {
  deleteTargetId.value = taskId
  deleteTaskName.value = taskName
  showDeleteConfirm.value = true
}

async function doDeleteTask() {
  if (!deleteTargetId.value) return
  await axios.delete(`/api/v1/tasks/${deleteTargetId.value}`)
  message.success('任务已删除')
  deleteTargetId.value = null
  await loadTasks()
}

function openDrawer(task: TaskItem) {
  selectedTask.value = task
  drawerVisible.value = true
  activeTab.value = 'params'
  hydrateDraft(task)
  loadStorageOptions()
}

function closeDrawer() {
  drawerVisible.value = false
  selectedTask.value = null
  runList.value = []
  runLogs.value = []
  selectedRunId.value = 0
  logKeyword.value = ''
}

function hydrateDraft(task: TaskItem) {
  const rawParams = (task.params || {}) as Record<string, unknown>
  const daysRaw = rawParams.default_download_days
  const days = Number.isFinite(Number(daysRaw)) ? Math.max(Number(daysRaw), 1) : 1
  const extraParams = { ...rawParams }
  delete extraParams.default_download_days

  paramsDraft.value = {
    default_download_days: days,
    extra_json: JSON.stringify(extraParams, null, 2),
  }
  storageDraftId.value = task.storage_config_id
  triggerDraft.value = {
    cron_expr: task.cron_expr,
    status: task.status === 'paused' ? 'paused' : 'enabled',
  }
}

async function loadStorageOptions() {
  const res = await axios.get('/api/v1/storages')
  const data = (res.data.data || []) as StorageOptionItem[]
  storageOptions.value = data
    .filter((row) => row.status === 'active')
    .map((row) => ({ value: row.id, label: `${row.name} (${row.type})` }))
}

async function switchTab(tab: 'params' | 'storage' | 'trigger' | 'logs') {
  activeTab.value = tab
  if (tab === 'logs') {
    await loadRunsForTask()
  }
}

async function saveParams() {
  if (!selectedTask.value) return
  let extra: Record<string, unknown> = {}
  try {
    extra = JSON.parse(paramsDraft.value.extra_json || '{}')
  } catch {
    message.error('页面参数 JSON 格式错误')
    return
  }
  await axios.patch(`/api/v1/tasks/${selectedTask.value.id}`, {
    params: {
      ...extra,
      default_download_days: Math.max(Number(paramsDraft.value.default_download_days || 1), 1),
    },
  })
  message.success('参数已保存')
  await loadTasks()
  const latest = tasks.value.find((t) => t.id === selectedTask.value?.id)
  if (latest) selectedTask.value = latest
}

const dateRangePreview = computed(() => {
  const days = Math.max(Number(paramsDraft.value.default_download_days || 1), 1)
  const today = new Date()
  const end = new Date(today)
  end.setDate(today.getDate() - 1)
  const start = new Date(end)
  start.setDate(end.getDate() - (days - 1))
  const toStr = (d: Date) => d.toISOString().slice(0, 10)
  return { start_date: toStr(start), end_date: toStr(end) }
})

async function saveStorage() {
  if (!selectedTask.value) return
  await axios.patch(`/api/v1/tasks/${selectedTask.value.id}`, { storage_config_id: storageDraftId.value })
  message.success('存储配置已保存')
  await loadTasks()
  const latest = tasks.value.find((t) => t.id === selectedTask.value?.id)
  if (latest) selectedTask.value = latest
}

async function saveTrigger() {
  if (!selectedTask.value) return
  await axios.patch(`/api/v1/tasks/${selectedTask.value.id}`, {
    cron_expr: triggerDraft.value.cron_expr,
    status: triggerDraft.value.status,
  })
  message.success('触发配置已保存')
  await loadTasks()
  const latest = tasks.value.find((t) => t.id === selectedTask.value?.id)
  if (latest) selectedTask.value = latest
}

async function loadRunsForTask() {
  if (!selectedTask.value) return
  logKeyword.value = ''
  const res = await axios.get('/api/v1/task-runs', {
    params: { task_id: selectedTask.value.id, limit: 20, offset: 0 },
  })
  runList.value = (res.data.data || []).map((r: any) => ({
    id: r.id,
    status: r.status,
    started_at: r.started_at,
  }))
  if (runList.value.length > 0) {
    await selectRun(runList.value[0].id)
  } else {
    selectedRunId.value = 0
    runLogs.value = []
  }
}

function handleRunChange(runId: number | string) {
  const id = Number(runId)
  if (!id) return
  selectRun(id)
}

async function selectRun(runId: number) {
  selectedRunId.value = runId
  const res = await axios.get(`/api/v1/task-runs/${runId}/logs`)
  runLogs.value = res.data.data?.items || []
}

onMounted(loadTasks)
</script>

<style scoped>
.tasks-page { position: relative; }
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.view-tabs { display: flex; gap: 6px; }
.view-tab {
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text-secondary);
  border-radius: var(--radius-pill);
  padding: 6px 14px;
  cursor: pointer;
}
.view-tab.active {
  border-color: var(--accent-copper);
  color: var(--accent-copper);
  background: var(--accent-copper-bg);
}
.filter-group { display: flex; gap: 8px; align-items: center; }
.search-input {
  width: 240px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 7px 10px;
  background: var(--bg-card);
  color: var(--text-primary);
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
}
.card-padding { padding: 20px; }
.mono { font-family: var(--font-mono); }
.empty-cell {
  text-align: center;
  color: var(--text-tertiary);
  padding: 24px;
}
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: 12px;
}
.page-btn {
  border: 1px solid var(--border);
  background: var(--bg-card);
  padding: 5px 10px;
  border-radius: 6px;
}

.task-board {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: 12px;
}
.task-card {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: 14px;
  padding: 14px;
  box-shadow: 0 2px 10px rgba(45, 42, 38, 0.06);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.task-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.task-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.task-title {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.task-sub {
  font-size: 12px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.task-run-badge {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid var(--border);
  white-space: nowrap;
}
.run-success {
  color: #2b8a3e;
  background: #edf9f0;
  border-color: #b6e3c0;
}
.run-running {
  color: #1769d8;
  background: #eaf3ff;
  border-color: #bad6ff;
}
.run-failed {
  color: #bb2d3b;
  background: #fff0f1;
  border-color: #ffc0c4;
}
.run-idle {
  color: var(--text-tertiary);
  background: var(--bg-card);
}
.task-meta {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
}
.meta-row {
  display: grid;
  grid-template-columns: 84px 1fr;
  gap: 8px;
  align-items: start;
}
.meta-label {
  color: var(--text-tertiary);
  font-size: 12px;
}
.meta-value {
  color: var(--text-primary);
  font-size: 13px;
  word-break: break-all;
}
.task-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.action-btn {
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text-secondary);
  border-radius: 6px;
  padding: 4px 10px;
  cursor: pointer;
}
.action-btn:hover {
  background: var(--select-option-hover);
  border-color: var(--accent-copper);
  color: var(--text-primary);
}
.action-primary {
  color: var(--accent-copper);
  border-color: var(--accent-copper-light);
  background: var(--accent-copper-bg);
}
.action-danger {
  color: var(--accent-red);
  border-color: var(--accent-red-light);
}

.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(25, 22, 18, 0.35);
  z-index: 2000;
  display: flex;
  justify-content: flex-end;
}
.drawer {
  width: min(880px, 90vw);
  height: 100%;
  background: var(--bg-base);
  border-left: 1px solid var(--border-light);
  box-shadow: -8px 0 40px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
}
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-light);
}
.drawer-title { font-size: 18px; font-weight: 600; color: var(--text-primary); }
.close-btn {
  border: none;
  background: transparent;
  font-size: 28px;
  line-height: 1;
  color: var(--text-tertiary);
  cursor: pointer;
}
.drawer-tabs {
  display: flex;
  gap: 6px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-light);
}
.tab-btn {
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text-secondary);
  border-radius: var(--radius-pill);
  padding: 6px 12px;
  cursor: pointer;
}
.tab-btn.active {
  color: var(--accent-copper);
  border-color: var(--accent-copper);
  background: var(--accent-copper-bg);
}
.drawer-content { padding: 16px 20px; overflow: auto; }
.panel { display: flex; flex-direction: column; gap: 12px; }
.form-row { display: flex; flex-direction: column; gap: 6px; }
.form-row label { font-size: 13px; color: var(--text-secondary); }
.input, .textarea {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  background: var(--bg-card);
  color: var(--text-primary);
}
.textarea {
  min-height: 180px;
  font-family: var(--font-mono);
  line-height: 1.5;
}
.mt8 { margin-top: 8px; }
.save-btn {
  width: fit-content;
  border: 1px solid var(--accent-copper);
  background: var(--accent-copper);
  color: var(--text-inverse);
  border-radius: 8px;
  padding: 8px 14px;
  cursor: pointer;
}

.log-toolbar {
  display: grid;
  grid-template-columns: auto minmax(280px, 380px) minmax(220px, 1fr) auto;
  gap: 10px;
  align-items: center;
}
.log-toolbar-label {
  color: var(--text-secondary);
  font-size: 14px;
}
.run-select { width: 100%; }
.log-search { width: 100%; }

.log-table-wrap {
  margin-top: 12px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  overflow: hidden;
}
.log-table {
  width: 100%;
  border-collapse: collapse;
}
.log-table th,
.log-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-light);
  text-align: left;
  font-size: 13px;
}
.log-table tr:last-child td { border-bottom: none; }
.time-col { width: 220px; }
.log-level { color: var(--accent-copper); font-weight: 600; margin-right: 8px; }
.log-message { color: var(--text-primary); }

@media (max-width: 960px) {
  .log-toolbar { grid-template-columns: 1fr; }
}
</style>
