<template>
  <div class="release-page">
    <div class="toolbar">
      <div class="filters">
        <input
          v-model="adapterKeyword"
          class="search-input"
          placeholder="按 adapter_key 过滤"
          @input="loadReleases"
        />
        <DcSelect
          v-model="statusFilter"
          class="status-select"
          :options="statusOptions"
          placeholder="状态筛选"
        />
      </div>
      <button class="primary-btn" @click="openModal">新增发版</button>
    </div>

    <div class="card table-wrap">
      <table>
        <thead>
          <tr>
            <th>适配器</th>
            <th>应用中文名</th>
            <th>版本</th>
            <th>状态</th>
            <th>QA</th>
            <th>发布人</th>
            <th>发布时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in releases" :key="`${row.adapter_key}-${row.version}`">
            <td>{{ row.adapter_key }}</td>
            <td>{{ row.display_name || '--' }}</td>
            <td>{{ row.version }}</td>
            <td>
              <span class="tag" :class="`tag-${row.status}`">{{ statusLabel(row.status) }}</span>
            </td>
            <td>{{ row.qa_passed ? '通过' : '未通过' }}</td>
            <td>{{ row.released_by || '--' }}</td>
            <td>{{ row.released_at ? formatDate(row.released_at) : '--' }}</td>
            <td>
              <button class="link-btn" @click="openModal(row)">编辑</button>
            </td>
          </tr>
          <tr v-if="releases.length === 0">
            <td colspan="8" class="empty">暂无发版记录</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>{{ editing ? '编辑发版' : '新增发版' }}</h3>
          <button class="close-btn" @click="showModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-grid">
            <div class="form-group">
              <label><span class="required">*</span> 适配器标识</label>
              <input v-model="form.adapter_key" class="input" :disabled="editing" placeholder="如：douyin.traffic_analytics" />
            </div>
            <div class="form-group">
              <label><span class="required">*</span> 版本</label>
              <input v-model="form.version" class="input" :disabled="editing" placeholder="如：1.1.0" />
            </div>
            <div class="form-group">
              <label><span class="required">*</span> 发布状态</label>
              <DcSelect v-model="form.status" class="status-select" :options="statusOptions" placeholder="请选择状态" />
            </div>
            <div class="form-group">
              <label><span class="required">*</span> QA 是否通过</label>
              <div class="radio-group">
                <label><input v-model="form.qa_passed" type="radio" :value="true" /> 通过</label>
                <label><input v-model="form.qa_passed" type="radio" :value="false" /> 未通过</label>
              </div>
            </div>
            <div class="form-group">
              <label>发布人</label>
              <input v-model="form.released_by" class="input" placeholder="如：kun-kun" />
            </div>
            <div class="form-group">
              <label>Checksum</label>
              <input v-model="form.checksum" class="input" placeholder="可选，便于追溯包内容" />
            </div>
            <div class="form-group full">
              <label>发布说明</label>
              <textarea v-model="form.release_notes" class="input textarea" placeholder="记录变更说明、风险点与回滚信息" />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="ghost-btn" @click="showModal = false">取消</button>
          <button class="primary-btn" @click="submitRelease">确认保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 页面用途：适配器发版管理页。
 * 核心职责：查询/新增/编辑 adapter_release，保证应用上架与任务执行的发布准入数据可维护。
 */
import { onMounted, ref, watch } from 'vue'
import axios from 'axios'
import { useMessage } from 'naive-ui'
import DcSelect from '@/components/DcSelect.vue'

type ReleaseStatus = 'draft' | 'testing' | 'released' | 'deprecated'

interface ReleaseItem {
  id: number
  adapter_key: string
  display_name: string | null
  version: string
  status: ReleaseStatus
  qa_passed: boolean
  checksum: string | null
  release_notes: string | null
  released_by: string | null
  released_at: string | null
}

interface SelectOption {
  value: string
  label: string
}

const message = useMessage()
const releases = ref<ReleaseItem[]>([])
const adapterKeyword = ref('')
const statusFilter = ref('')
const showModal = ref(false)
const editing = ref(false)

const statusOptions: SelectOption[] = [
  { value: 'draft', label: '草稿' },
  { value: 'testing', label: '测试中' },
  { value: 'released', label: '已发版' },
  { value: 'deprecated', label: '已废弃' },
]

const form = ref({
  adapter_key: '',
  version: '',
  status: 'draft' as ReleaseStatus,
  qa_passed: false,
  checksum: '',
  release_notes: '',
  released_by: '',
})

function statusLabel(status: ReleaseStatus) {
  if (status === 'draft') return '草稿'
  if (status === 'testing') return '测试中'
  if (status === 'released') return '已发版'
  return '已废弃'
}

function formatDate(dateText: string) {
  const d = new Date(dateText)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function loadReleases() {
  const params: Record<string, string> = {}
  if (adapterKeyword.value.trim()) params.adapter_key = adapterKeyword.value.trim()
  if (statusFilter.value) params.status = statusFilter.value
  const res = await axios.get('/api/v1/apps/releases', { params })
  releases.value = res.data.data || []
}

function openModal(row?: ReleaseItem) {
  if (!row) {
    editing.value = false
    form.value = {
      adapter_key: '',
      version: '',
      status: 'draft',
      qa_passed: false,
      checksum: '',
      release_notes: '',
      released_by: '',
    }
  } else {
    editing.value = true
    form.value = {
      adapter_key: row.adapter_key,
      version: row.version,
      status: row.status,
      qa_passed: row.qa_passed,
      checksum: row.checksum || '',
      release_notes: row.release_notes || '',
      released_by: row.released_by || '',
    }
  }
  showModal.value = true
}

/** 保存发版记录。后端会根据 adapter_key+version 做 upsert。 */
async function submitRelease() {
  if (!form.value.adapter_key.trim()) {
    message.warning('请填写适配器标识')
    return
  }
  if (!form.value.version.trim()) {
    message.warning('请填写版本')
    return
  }
  await axios.post('/api/v1/apps/releases', {
    adapter_key: form.value.adapter_key.trim(),
    version: form.value.version.trim(),
    status: form.value.status,
    qa_passed: form.value.qa_passed,
    checksum: form.value.checksum.trim() || null,
    release_notes: form.value.release_notes.trim() || null,
    released_by: form.value.released_by.trim() || null,
  })
  message.success('发版记录已保存')
  showModal.value = false
  await loadReleases()
}

watch(statusFilter, loadReleases)

onMounted(loadReleases)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; gap: 12px; }
.filters { display: flex; gap: 10px; align-items: center; }
.search-input { width: 320px; max-width: 60vw; padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); }
.status-select { width: 180px; }
.primary-btn {
  padding: 9px 16px;
  border: none;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--accent-copper), #B88560);
  color: var(--text-inverse);
  cursor: pointer;
  font-size: 14px;
  font-family: var(--font-body);
}
.ghost-btn {
  padding: 9px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  color: var(--text-secondary);
  cursor: pointer;
}
.card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-md); }
.table-wrap { overflow: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 12px 14px; border-bottom: 1px solid var(--border-light); font-size: 13px; text-align: left; }
.empty { text-align: center; color: var(--text-tertiary); }
.link-btn { border: none; background: transparent; color: var(--accent-copper); cursor: pointer; }
.tag { font-size: 12px; padding: 2px 10px; border-radius: 999px; }
.tag-draft { background: var(--bg-subtle); color: var(--text-secondary); }
.tag-testing { background: var(--accent-blue-bg); color: var(--accent-blue); }
.tag-released { background: var(--accent-green-bg); color: var(--accent-green); }
.tag-deprecated { background: var(--accent-red-bg); color: var(--accent-red); }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(45, 42, 38, 0.22);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-card {
  width: min(900px, 95vw);
  max-height: 92vh;
  background: var(--bg-base);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(180deg, var(--bg-subtle), var(--bg-base));
  border-bottom: 1px solid var(--border-light);
}
.modal-header h3 { margin: 0; font-family: var(--font-display); font-size: 20px; color: var(--text-primary); }
.close-btn { width: 30px; height: 30px; border: none; border-radius: var(--radius-sm); background: transparent; color: var(--text-tertiary); font-size: 22px; cursor: pointer; }
.modal-body { padding: 18px 20px; overflow: auto; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 20px; border-top: 1px solid var(--border-light); }

.form-grid { display: grid; grid-template-columns: repeat(2, minmax(260px, 1fr)); gap: 14px; }
.form-group { position: relative; }
.form-group.full { grid-column: 1 / -1; }
.form-group label { display: block; font-size: 14px; color: var(--text-secondary); margin-bottom: 8px; }
.required { color: #ff4d4f; margin-right: 2px; }
.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-sizing: border-box;
  font-size: 14px;
  font-family: var(--font-body);
  color: var(--text-primary);
  background: var(--bg-base);
  outline: none;
}
.input:focus { border-color: var(--accent-copper); box-shadow: 0 0 0 2px rgba(200, 149, 108, 0.1); }
.input:disabled { color: var(--text-secondary); background: var(--bg-subtle); }
.textarea { min-height: 110px; resize: vertical; }
.radio-group { display: flex; gap: 18px; padding: 10px 0; font-size: 14px; }

:deep(.status-select .dc-select) { width: 100%; display: flex; }
:deep(.status-select .dc-select-trigger) {
  min-height: 42px;
  padding: 10px 12px;
  border-color: var(--border);
  background: var(--bg-base);
}
</style>
