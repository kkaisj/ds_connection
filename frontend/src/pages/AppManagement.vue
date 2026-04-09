<template>
  <div class="app-manage-page">
    <div class="toolbar">
      <div class="left">
        <input v-model="keyword" class="search-input" placeholder="搜索应用名称/平台/运维人员" @input="debouncedLoad" />
      </div>
      <button class="primary-btn" @click="openCreate">上架应用</button>
    </div>

    <div class="card table-wrap">
      <table>
        <thead>
          <tr>
            <th>应用名称</th>
            <th>平台</th>
            <th>是否上架</th>
            <th>平均运行时间</th>
            <th>运维人员</th>
            <th>推荐程度</th>
            <th>采集周期</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredApps" :key="row.id">
            <td>{{ row.name }}</td>
            <td>{{ row.platform_name }}</td>
            <td>{{ row.is_published ? '是' : '否' }}</td>
            <td>{{ row.avg_runtime_minutes }} m</td>
            <td>{{ row.ops_owner || '--' }}</td>
            <td>{{ row.recommendation }}</td>
            <td>{{ row.collect_cycle || '--' }}</td>
            <td>
              <button class="link-btn" @click="openEdit(row)">编辑</button>
            </td>
          </tr>
          <tr v-if="filteredApps.length === 0">
            <td colspan="8" class="empty">暂无应用</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>{{ editingId ? '编辑应用' : '上架应用' }}</h3>
          <button class="close-btn" @click="showModal = false">×</button>
        </div>

        <div class="modal-body">
          <div class="form-grid">
            <div class="form-group full" ref="appPickerRef">
              <label><span class="required">*</span> 应用选择</label>
              <input
                v-if="!editingId"
                v-model="adapterSearch"
                class="input"
                placeholder="输入关键词搜索应用（默认显示前10个）"
                @focus="showAdapterPanel = true"
                @input="showAdapterPanel = true"
              />
              <input v-else class="input" :value="form.name" disabled />
              <div v-if="!editingId && showAdapterPanel" class="adapter-panel">
                <div
                  v-for="opt in visibleAdapters"
                  :key="opt.adapter_key"
                  class="adapter-item"
                  @click="selectAdapter(opt.adapter_key)"
                >
                  <div class="adapter-title">{{ opt.display_name }}</div>
                  <div class="adapter-sub">{{ platformName(opt.platform_code) }}</div>
                </div>
                <div v-if="visibleAdapters.length === 0" class="adapter-empty">无匹配应用</div>
              </div>
            </div>

            <div class="form-group">
              <label><span class="required">*</span> 一级平台</label>
              <DcSelect
                v-model="selectedPrimaryCode"
                class="form-select"
                :options="primaryPlatformOptions"
                placeholder="请选择一级平台"
                @change="onPrimaryChange"
              />
            </div>
            <div class="form-group">
              <label><span class="required">*</span> 二级平台</label>
              <DcSelect
                v-model="form.platform_code"
                class="form-select"
                :options="secondaryPlatformOptions"
                placeholder="请选择二级平台"
              />
            </div>

            <div class="form-group">
              <label><span class="required">*</span> 是否上架</label>
              <div class="radio-group">
                <label><input type="radio" :value="true" v-model="form.is_published" /> 是</label>
                <label><input type="radio" :value="false" v-model="form.is_published" /> 否</label>
              </div>
            </div>
            <div class="form-group">
              <label><span class="required">*</span> 平均运行时间</label>
              <div class="input-with-suffix">
                <input v-model.number="form.avg_runtime_minutes" type="number" min="1" class="input" />
                <span class="suffix">m(分钟)</span>
              </div>
            </div>

            <div class="form-group">
              <label><span class="required">*</span> 运维人员</label>
              <input v-model="form.ops_owner" class="input" placeholder="请输入" />
            </div>
            <div class="form-group">
              <label><span class="required">*</span> 是否需要额外参数</label>
              <div class="radio-group">
                <label><input type="radio" :value="true" v-model="form.need_extra_params" /> 是</label>
                <label><input type="radio" :value="false" v-model="form.need_extra_params" /> 否</label>
              </div>
            </div>

            <div class="form-group">
              <label><span class="required">*</span> 推荐程度</label>
              <select v-model.number="form.recommendation" class="input">
                <option v-for="n in 5" :key="n" :value="n">{{ n }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>平台预览图</label>
              <input v-model="form.platform_preview_url" class="input" placeholder="先留 URL 口子，后续可接 OSS" />
            </div>

            <div class="form-group">
              <label><span class="required">*</span> 数据表格</label>
              <input v-model="form.data_table" class="input" placeholder="例如：order_main" />
            </div>
            <div class="form-group">
              <label><span class="required">*</span> 采集周期</label>
              <input v-model="form.collect_cycle" class="input" placeholder="例如：每日08:00" />
            </div>

            <div class="form-group">
              <label><span class="required">*</span> 指标</label>
              <input v-model="form.metrics" class="input" placeholder="例如：订单量,退款率,客单价" />
            </div>
            <div class="form-group full">
              <label><span class="required">*</span> 使用说明</label>
              <textarea v-model="form.usage_guide" class="input textarea" placeholder="填写应用使用说明" />
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="ghost-btn" @click="showModal = false">取消</button>
          <button class="primary-btn" @click="submit">确认保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'
import DcSelect from '@/components/DcSelect.vue'

interface PlatformItem {
  id: number
  code: string
  name: string
  parent_id: number | null
  level: 1 | 2
}
interface AdapterItem {
  adapter_key: string
  platform_code: string
  display_name: string
  description: string
  default_version: string
  is_listed: boolean
}
interface AppItem {
  id: number
  name: string
  platform_code: string
  platform_name: string
  description: string | null
  version: string
  status: string
  is_published: boolean
  avg_runtime_minutes: number
  ops_owner: string
  need_extra_params: boolean
  recommendation: number
  platform_preview_url: string | null
  data_table: string
  collect_cycle: string
  metrics: string
  usage_guide: string
}
interface SelectOption {
  value: string
  label: string
}

const message = useMessage()
const keyword = ref('')
const apps = ref<AppItem[]>([])
const platforms = ref<PlatformItem[]>([])
const adapters = ref<AdapterItem[]>([])

const showModal = ref(false)
const showAdapterPanel = ref(false)
const editingId = ref<number | null>(null)
const adapterSearch = ref('')
const selectedAdapterKey = ref('')
const selectedPrimaryCode = ref('')
const appPickerRef = ref<HTMLElement | null>(null)

const form = ref({
  name: '',
  platform_code: '',
  is_published: true,
  avg_runtime_minutes: 6,
  ops_owner: '',
  need_extra_params: false,
  recommendation: 3,
  platform_preview_url: '',
  data_table: '',
  collect_cycle: '',
  metrics: '',
  usage_guide: '',
  version: '1.0.0',
  description: '',
})

const platformMap = computed(() => {
  const m = new Map<string, PlatformItem>()
  platforms.value.forEach((p) => m.set(p.code, p))
  return m
})

const primaryPlatforms = computed(() => platforms.value.filter((p) => p.parent_id === null))
const primaryPlatformOptions = computed<SelectOption[]>(() =>
  primaryPlatforms.value.map((p) => ({ value: p.code, label: p.name })),
)

const secondaryPlatforms = computed(() => {
  if (!selectedPrimaryCode.value) return []
  const primary = platformMap.value.get(selectedPrimaryCode.value)
  if (!primary) return []
  const children = platforms.value.filter((p) => p.parent_id === primary.id)
  return children.length > 0 ? children : [primary]
})

const secondaryPlatformOptions = computed<SelectOption[]>(() =>
  secondaryPlatforms.value.map((p) => ({ value: p.code, label: p.name })),
)

const filteredApps = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  if (!q) return apps.value
  return apps.value.filter((a) =>
    a.name.toLowerCase().includes(q)
    || a.platform_name.toLowerCase().includes(q)
    || (a.ops_owner || '').toLowerCase().includes(q),
  )
})

const visibleAdapters = computed(() => {
  const q = adapterSearch.value.trim().toLowerCase()
  return q
    ? adapters.value.filter((a) => a.display_name.toLowerCase().includes(q) || a.adapter_key.toLowerCase().includes(q))
    : adapters.value.slice(0, 10)
})

function getPrimaryCodeBySecondary(secondaryCode: string) {
  const secondary = platformMap.value.get(secondaryCode)
  if (!secondary) return ''
  if (secondary.parent_id === null) return secondary.code
  const parent = platforms.value.find((p) => p.id === secondary.parent_id)
  return parent?.code || ''
}

function onPrimaryChange() {
  const allowedCodes = new Set(secondaryPlatforms.value.map((p) => p.code))
  if (!allowedCodes.has(form.value.platform_code)) {
    form.value.platform_code = ''
  }
}

function handleOutsideClick(e: MouseEvent) {
  const target = e.target as Node
  if (showAdapterPanel.value && appPickerRef.value && !appPickerRef.value.contains(target)) {
    showAdapterPanel.value = false
  }
}

function platformName(code: string) {
  return platformMap.value.get(code)?.name || code
}

function resetForm() {
  form.value = {
    name: '',
    platform_code: '',
    is_published: true,
    avg_runtime_minutes: 6,
    ops_owner: '',
    need_extra_params: false,
    recommendation: 3,
    platform_preview_url: '',
    data_table: '',
    collect_cycle: '',
    metrics: '',
    usage_guide: '',
    version: '1.0.0',
    description: '',
  }
  selectedPrimaryCode.value = ''
  selectedAdapterKey.value = ''
  adapterSearch.value = ''
  showAdapterPanel.value = false
}

function openCreate() {
  editingId.value = null
  resetForm()
  showModal.value = true
}

function openEdit(row: AppItem) {
  editingId.value = row.id
  selectedAdapterKey.value = ''
  adapterSearch.value = row.name
  showAdapterPanel.value = false
  form.value = {
    name: row.name,
    platform_code: row.platform_code,
    is_published: row.is_published,
    avg_runtime_minutes: row.avg_runtime_minutes || 6,
    ops_owner: row.ops_owner || '',
    need_extra_params: !!row.need_extra_params,
    recommendation: row.recommendation || 3,
    platform_preview_url: row.platform_preview_url || '',
    data_table: row.data_table || '',
    collect_cycle: row.collect_cycle || '',
    metrics: row.metrics || '',
    usage_guide: row.usage_guide || '',
    version: row.version,
    description: row.description || '',
  }
  selectedPrimaryCode.value = getPrimaryCodeBySecondary(row.platform_code)
  showModal.value = true
}

function selectAdapter(adapterKey: string) {
  const tpl = adapters.value.find((a) => a.adapter_key === adapterKey)
  if (!tpl) return
  selectedAdapterKey.value = tpl.adapter_key
  adapterSearch.value = tpl.display_name
  showAdapterPanel.value = false
  form.value.name = tpl.display_name
  form.value.description = tpl.description
  form.value.version = tpl.default_version
  form.value.platform_code = tpl.platform_code
  selectedPrimaryCode.value = getPrimaryCodeBySecondary(tpl.platform_code)
}

function validate() {
  if (!editingId.value && !selectedAdapterKey.value) return '请选择应用'
  if (!selectedPrimaryCode.value) return '请选择一级平台'
  if (!form.value.platform_code) return '请选择二级平台'
  if (!form.value.ops_owner.trim()) return '请填写运维人员'
  if (!form.value.avg_runtime_minutes || form.value.avg_runtime_minutes < 1) return '平均运行时间需大于 0'
  if (!form.value.data_table.trim()) return '请填写数据表格'
  if (!form.value.collect_cycle.trim()) return '请填写采集周期'
  if (!form.value.metrics.trim()) return '请填写指标'
  if (!form.value.usage_guide.trim()) return '请填写使用说明'
  return ''
}

async function submit() {
  const err = validate()
  if (err) {
    message.warning(err)
    return
  }

  const payload = {
    platform_code: form.value.platform_code,
    name: form.value.name.trim(),
    adapter_key: selectedAdapterKey.value,
    version: form.value.version,
    description: form.value.description || null,
    status: form.value.is_published ? 'active' : 'inactive',
    is_published: form.value.is_published,
    avg_runtime_minutes: form.value.avg_runtime_minutes,
    ops_owner: form.value.ops_owner.trim(),
    need_extra_params: form.value.need_extra_params,
    recommendation: form.value.recommendation,
    platform_preview_url: form.value.platform_preview_url.trim() || null,
    data_table: form.value.data_table.trim(),
    collect_cycle: form.value.collect_cycle.trim(),
    metrics: form.value.metrics.trim(),
    usage_guide: form.value.usage_guide.trim(),
  }

  if (editingId.value) {
    const updatePayload = { ...payload }
    delete (updatePayload as { adapter_key?: string }).adapter_key
    await axios.patch(`/api/v1/apps/${editingId.value}`, updatePayload)
    message.success('应用更新成功')
  } else {
    await axios.post('/api/v1/apps', payload)
    message.success('应用上架成功')
  }

  showModal.value = false
  await loadApps()
  await loadAdapters()
}

async function loadPlatforms() {
  const res = await axios.get('/api/v1/apps/platforms')
  platforms.value = res.data.data
}

async function loadApps() {
  const res = await axios.get('/api/v1/apps', { params: { include_inactive: true } })
  apps.value = res.data.data
}

async function loadAdapters() {
  const res = await axios.get('/api/v1/apps/available-adapters')
  adapters.value = res.data.data
}

let timer: ReturnType<typeof setTimeout>
function debouncedLoad() {
  clearTimeout(timer)
  timer = setTimeout(() => {}, 200)
}

onMounted(async () => {
  document.addEventListener('mousedown', handleOutsideClick)
  await Promise.all([loadPlatforms(), loadApps(), loadAdapters()])
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleOutsideClick)
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; gap: 12px; }
.search-input { width: 320px; max-width: 60vw; padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); }
.primary-btn { padding: 9px 16px; border: none; border-radius: var(--radius-sm); background: linear-gradient(135deg, var(--accent-copper), #B88560); color: #fff; cursor: pointer; font-size: 14px; }
.ghost-btn { padding: 9px 16px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: #fff; cursor: pointer; font-size: 14px; }
.card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-md); }
.table-wrap { overflow: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 12px 14px; border-bottom: 1px solid var(--border-light); font-size: 13px; text-align: left; }
.empty { text-align: center; color: var(--text-tertiary); }
.link-btn { border: none; background: transparent; color: var(--accent-copper); cursor: pointer; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.25); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-card { width: min(980px, 95vw); max-height: 92vh; background: #fff; border-radius: var(--radius-lg); display: flex; flex-direction: column; overflow: hidden; font-size: 15px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border-light); }
.modal-header h3 { margin: 0; font-size: 24px; }
.close-btn { border: none; background: transparent; font-size: 24px; cursor: pointer; }
.modal-body { padding: 18px 20px; overflow: auto; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 20px; border-top: 1px solid var(--border-light); }

.form-grid { display: grid; grid-template-columns: repeat(2, minmax(260px, 1fr)); gap: 14px; }
.form-group { position: relative; }
.form-group.full { grid-column: 1 / -1; }
.form-group label { display: block; font-size: 14px; color: var(--text-secondary); margin-bottom: 8px; }
.required { color: #ff4d4f; margin-right: 2px; }
.input { width: 100%; padding: 10px 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); box-sizing: border-box; font-size: 14px; }
.form-select { width: 100%; display: block; }
:deep(.form-select .dc-select) { width: 100%; display: flex; }
.textarea { min-height: 110px; resize: vertical; }
.radio-group { display: flex; gap: 18px; padding: 10px 0; font-size: 14px; }
.input-with-suffix { display: grid; grid-template-columns: 1fr auto; }
.suffix { border: 1px solid var(--border); border-left: 0; border-radius: 0 var(--radius-sm) var(--radius-sm) 0; padding: 10px 12px; background: var(--bg-subtle); color: var(--text-secondary); font-size: 14px; }
.input-with-suffix .input { border-radius: var(--radius-sm) 0 0 var(--radius-sm); }

.adapter-panel { position: absolute; left: 0; right: 0; top: 72px; max-height: 240px; overflow: auto; border: 1px solid var(--border); background: #fff; border-radius: var(--radius-sm); z-index: 20; box-shadow: var(--shadow-sm); }
.adapter-item { padding: 10px 12px; cursor: pointer; border-bottom: 1px solid var(--border-light); }
.adapter-item:hover { background: var(--bg-hover); }
.adapter-title { font-size: 14px; color: var(--text-primary); }
.adapter-sub { font-size: 12px; color: var(--text-tertiary); margin-top: 3px; }
.adapter-empty { padding: 12px; color: var(--text-tertiary); text-align: center; font-size: 14px; }
</style>
