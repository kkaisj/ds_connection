<!--
  连接任务页面
  支持三种视图：列表视图 / 平台视图 / 账号视图
  支持关键词搜索（任务名/应用名/店铺名）+ 状态筛选
  每个任务可操作：暂停/启用、手动执行、删除
-->
<template>
  <div class="tasks-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <!-- 左：视图切换 -->
      <div class="view-tabs">
        <button
          v-for="v in views"
          :key="v.key"
          class="view-tab"
          :class="{ active: activeView === v.key }"
          @click="activeView = v.key"
        >
          <span class="view-icon">{{ v.icon }}</span>
          {{ v.label }}
        </button>
      </div>

      <!-- 右：搜索 + 状态筛选 -->
      <div class="filter-group">
        <div class="search-box">
          <input
            v-model="keyword"
            type="text"
            class="search-input"
            placeholder="搜索任务、应用、店铺..."
            @input="debouncedLoad"
          />
        </div>
        <DcSelect
          v-model="filterStatus"
          :options="statusOptions"
          placeholder="全部状态"
          @change="loadTasks"
        />
        <span class="result-count">{{ tasks.length }} 个任务</span>
      </div>
    </div>

    <!-- ═══════ 列表视图 ═══════ -->
    <div v-if="activeView === 'list'" class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>任务名称</th>
              <th>连接应用</th>
              <th>平台</th>
              <th>店铺</th>
              <th>调度</th>
              <th>状态</th>
              <th>上次执行</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in pagedTasks" :key="task.id">
              <td><span class="task-name">{{ task.name }}</span></td>
              <td class="cell-secondary">{{ task.app_name }}</td>
              <td><span class="platform-tag" :class="`ptag-${task.platform_code}`">{{ task.platform_name }}</span></td>
              <td class="cell-secondary">{{ task.shop_name }}</td>
              <td><span class="cell-mono">{{ task.cron_expr }}</span></td>
              <td>
                <span class="status-badge" :class="`status-${task.status}`">
                  <span class="status-dot"></span>
                  {{ task.status === 'enabled' ? '运行中' : '已暂停' }}
                </span>
              </td>
              <td class="cell-time">{{ task.last_run_at ? formatTime(task.last_run_at) : '--' }}</td>
              <td>
                <div class="action-group">
                  <button class="action-btn" @click="toggleStatus(task)">{{ task.status === 'enabled' ? '暂停' : '启用' }}</button>
                  <button class="action-btn action-primary" @click="manualRun(task.id)">执行</button>
                  <button class="action-btn action-danger" @click="deleteTask(task.id)">删除</button>
                </div>
              </td>
            </tr>
            <tr v-if="pagedTasks.length === 0">
              <td colspan="8" class="empty-cell">暂无匹配任务</td>
            </tr>
          </tbody>
        </table>
      </div>
      <!-- 分页 -->
      <div v-if="totalPages > 1" class="pagination">
        <button class="page-btn" :disabled="page === 1" @click="page--">上一页</button>
        <span class="page-info">{{ page }} / {{ totalPages }}</span>
        <button class="page-btn" :disabled="page === totalPages" @click="page++">下一页</button>
      </div>
    </div>

    <!-- ═══════ 平台视图 ═══════ -->
    <div v-if="activeView === 'platform'" class="group-view">
      <div v-for="group in platformGroups" :key="group.label" class="group-section">
        <div class="group-header" @click="toggleGroup('p_' + group.label)">
          <span class="group-icon" :class="`icon-${group.color}`">{{ group.label[0] }}</span>
          <span class="group-title">{{ group.label }}</span>
          <span class="group-count">{{ group.tasks.length }} 个任务</span>
          <span class="group-chevron" :class="{ expanded: !collapsedGroups[`p_${group.label}`] }">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </div>
        <div v-show="!collapsedGroups[`p_${group.label}`]" class="group-cards">
          <div v-for="task in group.tasks" :key="task.id" class="task-card">
            <div class="tc-top">
              <span class="tc-name">{{ task.name }}</span>
              <span class="status-badge small" :class="`status-${task.status}`">
                <span class="status-dot"></span>
                {{ task.status === 'enabled' ? '运行中' : '已暂停' }}
              </span>
            </div>
            <div class="tc-info">
              <span>{{ task.shop_name }}</span>
              <span class="tc-cron">{{ task.cron_expr }}</span>
            </div>
            <div class="tc-actions">
              <button class="action-btn small" @click="toggleStatus(task)">{{ task.status === 'enabled' ? '暂停' : '启用' }}</button>
              <button class="action-btn action-primary small" @click="manualRun(task.id)">执行</button>
              <button class="action-btn action-danger small" @click="deleteTask(task.id)">删除</button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="platformGroups.length === 0" class="empty-state">暂无匹配任务</div>
    </div>

    <!-- ═══════ 账号视图 ═══════ -->
    <div v-if="activeView === 'account'" class="group-view">
      <div v-for="group in accountGroups" :key="group.label" class="group-section">
        <div class="group-header" @click="toggleGroup('a_' + group.label)">
          <span class="group-icon icon-copper">{{ group.label[0] }}</span>
          <span class="group-title">{{ group.label }}</span>
          <span class="group-sub">{{ group.platform }}</span>
          <span class="group-count">{{ group.tasks.length }} 个任务</span>
          <span class="group-chevron" :class="{ expanded: !collapsedGroups[`a_${group.label}`] }">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
          </span>
        </div>
        <div v-show="!collapsedGroups[`a_${group.label}`]" class="group-cards">
          <div v-for="task in group.tasks" :key="task.id" class="task-card">
            <div class="tc-top">
              <span class="tc-name">{{ task.name }}</span>
              <span class="status-badge small" :class="`status-${task.status}`">
                <span class="status-dot"></span>
                {{ task.status === 'enabled' ? '运行中' : '已暂停' }}
              </span>
            </div>
            <div class="tc-info">
              <span class="platform-tag mini" :class="`ptag-${task.platform_code}`">{{ task.platform_name }}</span>
              <span class="tc-cron">{{ task.cron_expr }}</span>
            </div>
            <div class="tc-actions">
              <button class="action-btn small" @click="toggleStatus(task)">{{ task.status === 'enabled' ? '暂停' : '启用' }}</button>
              <button class="action-btn action-primary small" @click="manualRun(task.id)">执行</button>
              <button class="action-btn action-danger small" @click="deleteTask(task.id)">删除</button>
            </div>
          </div>
        </div>
      </div>
      <div v-if="accountGroups.length === 0" class="empty-state">暂无匹配任务</div>
    </div>

    <!-- 删除确认弹窗 -->
    <DcConfirm
      v-model:show="showDeleteConfirm"
      title="确认删除任务？"
      :desc="`确定要删除任务「${deleteTaskName}」吗？删除后不可恢复。`"
      confirm-text="删除"
      :danger="true"
      @confirm="doDeleteTask"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 连接任务页面逻辑
 * - 三种视图：列表 / 按平台分组 / 按账号分组
 * - 搜索：关键词模糊匹配 + 状态筛选
 * - 操作：启用/暂停、手动执行、删除
 */
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'
import DcSelect from '@/components/DcSelect.vue'
import DcConfirm from '@/components/DcConfirm.vue'

const message = useMessage()

/* ── 类型 ── */
interface TaskItem {
  id: number; name: string; app_name: string; platform_code: string;
  platform_name: string; shop_name: string; cron_expr: string;
  status: string; last_run_at: string | null
}

/* ── 视图定义 ── */
const views = [
  { key: 'list', label: '列表', icon: '≡' },
  { key: 'platform', label: '平台', icon: '◉' },
  { key: 'account', label: '账号', icon: '◎' },
]
const activeView = ref('list')

/* ── 下拉选项 ── */
const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'enabled', label: '已启用' },
  { value: 'paused', label: '已暂停' },
]

/* ── 列表状态 ── */
const tasks = ref<TaskItem[]>([])
const keyword = ref('')
const filterStatus = ref('')
const page = ref(1)
const pageSize = 10

/* ── 分组折叠状态 ── */
const collapsedGroups = ref<Record<string, boolean>>({})
function toggleGroup(key: string) {
  collapsedGroups.value[key] = !collapsedGroups.value[key]
}

/* ── 删除确认 ── */
const showDeleteConfirm = ref(false)
const deleteTargetId = ref<number | null>(null)
const deleteTaskName = ref('')

/* ── 分页 ── */
const totalPages = computed(() => Math.max(1, Math.ceil(tasks.value.length / pageSize)))
const pagedTasks = computed(() => {
  const start = (page.value - 1) * pageSize
  return tasks.value.slice(start, start + pageSize)
})

/* ── 平台分组视图 ── */
const platformGroups = computed(() => {
  const map = new Map<string, { label: string; color: string; tasks: TaskItem[] }>()
  const colorMap: Record<string, string> = { taobao: 'copper', jd: 'red', pdd: 'green', douyin: 'blue' }
  for (const t of tasks.value) {
    if (!map.has(t.platform_code)) {
      map.set(t.platform_code, {
        label: t.platform_name,
        color: colorMap[t.platform_code] || 'copper',
        tasks: [],
      })
    }
    map.get(t.platform_code)!.tasks.push(t)
  }
  return Array.from(map.values())
})

/* ── 账号分组视图 ── */
const accountGroups = computed(() => {
  const map = new Map<string, { label: string; platform: string; tasks: TaskItem[] }>()
  for (const t of tasks.value) {
    const key = t.shop_name
    if (!map.has(key)) {
      map.set(key, { label: t.shop_name, platform: t.platform_name, tasks: [] })
    }
    map.get(key)!.tasks.push(t)
  }
  return Array.from(map.values())
})

/* ── 工具函数 ── */
function formatTime(iso: string) { return iso.replace('T', ' ').substring(0, 16) }

/* ── 数据加载 ── */
async function loadTasks() {
  const params: Record<string, string> = {}
  if (keyword.value) params.keyword = keyword.value
  if (filterStatus.value) params.status = filterStatus.value

  const res = await axios.get('/api/v1/tasks', { params })
  tasks.value = res.data.data
  page.value = 1
}

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() { clearTimeout(debounceTimer); debounceTimer = setTimeout(loadTasks, 300) }

/* ── 操作 ── */
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

async function deleteTask(taskId: number) {
  // 找到任务名用于弹窗展示
  const task = tasks.value.find(t => t.id === taskId)
  deleteTargetId.value = taskId
  deleteTaskName.value = task?.name || ''
  showDeleteConfirm.value = true
}

async function doDeleteTask() {
  if (!deleteTargetId.value) return
  await axios.delete(`/api/v1/tasks/${deleteTargetId.value}`)
  message.success('任务已删除')
  deleteTargetId.value = null
  await loadTasks()
}

onMounted(loadTasks)
</script>

<style scoped>
/* ═══════ 工具栏 ═══════ */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

/* 视图切换 */
.view-tabs { display: flex; gap: 4px; }
.view-tab {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 16px; border-radius: var(--radius-pill);
  font-size: 13px; font-weight: 500;
  background: var(--bg-card); border: 1px solid var(--border-light);
  color: var(--text-secondary); cursor: pointer;
  transition: all 0.2s; font-family: var(--font-body);
}
.view-tab:hover { border-color: var(--accent-copper-light); color: var(--text-primary); }
.view-tab.active {
  background: var(--accent-copper-bg); border-color: var(--accent-copper-light); color: var(--accent-copper);
  font-weight: 600;
}
.view-icon { font-size: 14px; line-height: 1; }

/* 搜索 + 筛选 */
.filter-group { display: flex; align-items: center; gap: 10px; }
.search-box { position: relative; }
.search-input {
  padding: 7px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--bg-card); font-size: 13px; font-family: var(--font-body);
  color: var(--text-primary); width: 240px; outline: none; transition: border-color 0.2s;
}
.search-input:focus { border-color: var(--accent-copper); }
.search-input::placeholder { color: var(--text-tertiary); }
.filter-select {
  padding: 7px 12px; border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--bg-card); font-size: 13px; font-family: var(--font-body);
  color: var(--text-primary); outline: none; cursor: pointer;
}
.result-count { font-size: 12.5px; color: var(--text-tertiary); white-space: nowrap; }

/* ═══════ 列表视图 ═══════ */
.card {
  background: var(--bg-card); border-radius: var(--radius-md);
  border: 1px solid var(--border-light); box-shadow: var(--shadow-sm);
  animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.table-wrap { padding: 0 6px 6px; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }

thead th {
  text-align: left; padding: 12px 16px; font-size: 11px; font-weight: 600;
  color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.8px;
  border-bottom: 1px solid var(--border-light); white-space: nowrap;
}
tbody tr { transition: background 0.15s; }
tbody tr:hover { background: var(--bg-hover); }
tbody td {
  padding: 13px 16px; font-size: 13px; color: var(--text-primary);
  border-bottom: 1px solid var(--border-light); white-space: nowrap;
}
tbody tr:last-child td { border-bottom: none; }
.empty-cell { text-align: center; color: var(--text-tertiary); padding: 40px 16px !important; }

.task-name { font-weight: 500; }
.cell-secondary { color: var(--text-secondary); }
.cell-mono { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }
.cell-time { font-size: 12.5px; color: var(--text-tertiary); }

/* 平台标签颜色 */
.platform-tag {
  display: inline-flex; padding: 3px 10px; border-radius: var(--radius-pill);
  font-size: 11.5px; font-weight: 500; background: var(--bg-subtle); color: var(--text-secondary);
}
.platform-tag.mini { font-size: 10.5px; padding: 2px 8px; }
.ptag-taobao { background: var(--accent-copper-bg); color: var(--accent-copper); }
.ptag-jd { background: var(--accent-red-bg); color: var(--accent-red); }
.ptag-pdd { background: var(--accent-green-bg); color: var(--accent-green); }
.ptag-douyin { background: var(--accent-blue-bg); color: var(--accent-blue); }

/* 状态 */
.status-badge {
  display: inline-flex; align-items: center; gap: 5px; padding: 4px 12px;
  border-radius: var(--radius-pill); font-size: 11.5px; font-weight: 550;
}
.status-badge.small { padding: 3px 9px; font-size: 11px; }
.status-enabled { background: var(--accent-green-bg); color: var(--accent-green); }
.status-paused { background: var(--accent-amber-bg); color: var(--accent-amber); }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

/* 操作按钮 */
.action-group { display: flex; gap: 6px; }
.action-btn {
  padding: 4px 12px; border-radius: 6px; font-size: 11.5px; font-weight: 500;
  border: 1px solid var(--border); background: var(--bg-card); color: var(--text-secondary);
  cursor: pointer; transition: all 0.2s; font-family: var(--font-body);
}
.action-btn.small { padding: 3px 10px; font-size: 11px; }
.action-btn:hover { border-color: var(--accent-copper-light); color: var(--text-primary); }
.action-primary { background: var(--accent-copper-bg); border-color: var(--accent-copper-light); color: var(--accent-copper); }
.action-primary:hover { background: var(--accent-copper); color: white; }
.action-danger { color: var(--accent-red); border-color: var(--accent-red-light); }
.action-danger:hover { background: var(--accent-red); color: white; border-color: var(--accent-red); }

/* 分页 */
.pagination {
  display: flex; align-items: center; justify-content: center; gap: 16px;
  padding: 14px; border-top: 1px solid var(--border-light);
}
.page-btn {
  padding: 5px 14px; border-radius: 6px; font-size: 12px; font-weight: 500;
  border: 1px solid var(--border); background: var(--bg-card); color: var(--text-secondary);
  cursor: pointer; transition: all 0.2s; font-family: var(--font-body);
}
.page-btn:hover:not(:disabled) { border-color: var(--accent-copper); color: var(--accent-copper); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: 12.5px; color: var(--text-tertiary); font-family: var(--font-mono); }

/* ═══════ 分组视图（平台/账号） ═══════ */
.group-view {
  display: flex; flex-direction: column; gap: 24px;
}

.group-section {
  opacity: 0; transform: translateY(16px);
  animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.group-header {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 12px; padding-bottom: 10px;
  border-bottom: 1px solid var(--border-light);
  cursor: pointer; user-select: none; transition: background 0.15s;
  border-radius: var(--radius-sm); padding: 10px 12px; margin: 0 -12px 12px;
}
.group-header:hover { background: var(--bg-hover); }

.group-chevron {
  display: flex; align-items: center; color: var(--text-tertiary);
  transition: transform 0.25s ease; margin-left: 8px;
}
.group-chevron.expanded { transform: rotate(0deg); }
.group-chevron:not(.expanded) { transform: rotate(-90deg); }

.group-icon {
  width: 32px; height: 32px; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600;
}
.icon-copper { background: var(--accent-copper-bg); color: var(--accent-copper); }
.icon-red { background: var(--accent-red-bg); color: var(--accent-red); }
.icon-green { background: var(--accent-green-bg); color: var(--accent-green); }
.icon-blue { background: var(--accent-blue-bg); color: var(--accent-blue); }

.group-title {
  font-family: var(--font-display); font-size: 16px; font-weight: 600; color: var(--text-primary);
}
.group-sub { font-size: 12px; color: var(--text-tertiary); }
.group-count {
  margin-left: auto; font-size: 12px; color: var(--text-tertiary);
  font-family: var(--font-mono);
}

/* 任务卡片（分组内） */
.group-cards {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px;
}

.task-card {
  background: var(--bg-card); border-radius: var(--radius-sm);
  border: 1px solid var(--border-light); padding: 14px 16px;
  transition: all 0.2s; cursor: default;
}
.task-card:hover {
  box-shadow: var(--shadow-sm); border-color: var(--accent-copper-light);
}

.tc-top {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
}
.tc-name { font-size: 13.5px; font-weight: 550; color: var(--text-primary); }

.tc-info {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 10px; font-size: 12.5px; color: var(--text-secondary);
}
.tc-cron {
  font-family: var(--font-mono); font-size: 11.5px; color: var(--text-tertiary);
  margin-left: auto;
}

.tc-actions { display: flex; gap: 6px; }

.empty-state { text-align: center; padding: 60px 0; color: var(--text-tertiary); font-size: 14px; }
</style>
