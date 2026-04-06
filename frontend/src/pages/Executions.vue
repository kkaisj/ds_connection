<!--
  执行记录页面
  展示任务运行历史列表，支持按任务/状态筛选和分页。
  可查看失败原因和重试次数等详细信息。
-->
<template>
  <div class="executions-page">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-group">
        <DcSelect
          v-model="filterStatus"
          :options="runStatusOptions"
          placeholder="全部状态"
          @change="loadRuns"
        />
      </div>
      <div class="result-count">
        共 {{ runs.length }} 条记录
      </div>
    </div>

    <!-- 执行记录表格 -->
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>任务</th>
              <th>平台</th>
              <th>店铺</th>
              <th>触发方式</th>
              <th>状态</th>
              <th>耗时</th>
              <th>错误信息</th>
              <th>开始时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in runs" :key="run.id">
              <td class="cell-mono">{{ run.id }}</td>
              <td>
                <span class="task-name">{{ run.task_name }}</span>
              </td>
              <td><span class="platform-tag">{{ run.platform_name }}</span></td>
              <td class="cell-secondary">{{ run.shop_name }}</td>
              <td>
                <span class="trigger-tag" :class="`trigger-${run.trigger_type}`">
                  {{ triggerLabel(run.trigger_type) }}
                </span>
              </td>
              <td>
                <span class="status-badge" :class="`status-${run.status}`">
                  <span class="status-dot"></span>
                  {{ statusLabel(run.status) }}
                </span>
              </td>
              <td class="cell-mono">{{ formatDuration(run.duration_ms) }}</td>
              <td class="cell-error">
                <span v-if="run.error_message" :title="run.error_message">
                  {{ run.error_code }}: {{ truncate(run.error_message, 20) }}
                </span>
                <span v-else class="cell-secondary">--</span>
              </td>
              <td class="cell-time">{{ formatTime(run.started_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="pagination">
        <button class="page-btn" :disabled="page === 1" @click="prevPage">上一页</button>
        <span class="page-info">第 {{ page }} 页</span>
        <button class="page-btn" :disabled="runs.length < pageSize" @click="nextPage">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import DcSelect from '@/components/DcSelect.vue'

/* ── 类型 ── */
interface RunItem {
  id: number
  task_id: number
  task_name: string
  app_name: string
  platform_name: string
  shop_name: string
  trigger_type: string
  status: string
  retry_count: number
  duration_ms: number | null
  error_code: string | null
  error_message: string | null
  started_at: string | null
  ended_at: string | null
}

/* ── 状态 ── */
const runs = ref<RunItem[]>([])
const filterStatus = ref('')
const page = ref(1)
const pageSize = 15
const total = ref(0)

/* ── 下拉选项 ── */
const runStatusOptions = [
  { value: '', label: '全部状态' },
  { value: 'success', label: '成功' },
  { value: 'failed', label: '失败' },
  { value: 'running', label: '运行中' },
  { value: 'pending', label: '等待中' },
  { value: 'cancelled', label: '已取消' },
]

/* ── 字典映射 ── */
const statusMap: Record<string, string> = {
  success: '成功', failed: '失败', running: '运行中', pending: '等待中', cancelled: '已取消',
}
function statusLabel(s: string) { return statusMap[s] || s }

const triggerMap: Record<string, string> = {
  scheduler: '定时', manual: '手动', retry: '重试',
}
function triggerLabel(t: string) { return triggerMap[t] || t }

/* ── 工具函数 ── */
function formatDuration(ms: number | null) {
  if (ms == null) return '--'
  return `${(ms / 1000).toFixed(1)}s`
}

function formatTime(iso: string | null) {
  if (!iso) return '--'
  return iso.replace('T', ' ').substring(0, 19)
}

function truncate(str: string, len: number) {
  return str.length > len ? str.substring(0, len) + '...' : str
}

/* ── 数据加载 ── */
async function loadRuns() {
  const params: Record<string, string | number> = {
    limit: pageSize,
    offset: (page.value - 1) * pageSize,
  }
  if (filterStatus.value) params.status = filterStatus.value

  const res = await axios.get('/api/v1/task-runs', { params })
  runs.value = res.data.data
  total.value = res.data.data.length
}

/* ── 翻页 ── */
function prevPage() { if (page.value > 1) { page.value--; loadRuns() } }
function nextPage() { if (runs.value.length === pageSize) { page.value++; loadRuns() } }

onMounted(loadRuns)
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.filter-group { display: flex; gap: 10px; }

.filter-select {
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-card);
  font-size: 13px;
  font-family: var(--font-body);
  color: var(--text-primary);
  outline: none;
  cursor: pointer;
}

.result-count {
  font-size: 12.5px;
  color: var(--text-tertiary);
}

.card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.table-wrap { padding: 0 6px 6px; overflow-x: auto; }

table { width: 100%; border-collapse: collapse; }

thead th {
  text-align: left;
  padding: 12px 14px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  border-bottom: 1px solid var(--border-light);
  white-space: nowrap;
}

tbody tr { transition: background 0.15s; }
tbody tr:hover { background: var(--bg-hover); }

tbody td {
  padding: 12px 14px;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-light);
  white-space: nowrap;
}

tbody tr:last-child td { border-bottom: none; }

.task-name { font-weight: 500; }
.cell-secondary { color: var(--text-secondary); }
.cell-mono { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }
.cell-time { font-size: 12px; color: var(--text-tertiary); }
.cell-error { font-size: 12px; color: var(--accent-red); max-width: 200px; }

.platform-tag {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: 11.5px;
  font-weight: 500;
  background: var(--bg-subtle);
  color: var(--text-secondary);
}

/* 触发方式标签 */
.trigger-tag {
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 500;
}

.trigger-scheduler { background: var(--accent-blue-bg); color: var(--accent-blue); }
.trigger-manual { background: var(--accent-copper-bg); color: var(--accent-copper); }
.trigger-retry { background: var(--accent-amber-bg); color: var(--accent-amber); }

/* 状态标签 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  font-size: 11.5px;
  font-weight: 550;
}

.status-success { background: var(--accent-green-bg); color: var(--accent-green); }
.status-failed { background: var(--accent-red-bg); color: var(--accent-red); }
.status-running { background: var(--accent-blue-bg); color: var(--accent-blue); }
.status-pending { background: var(--accent-amber-bg); color: var(--accent-amber); }
.status-cancelled { background: var(--bg-subtle); color: var(--text-tertiary); }

.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.status-running .status-dot { animation: pulseDot 1.5s ease-in-out infinite; }

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
</style>
