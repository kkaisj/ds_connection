<!--
  连接市场页面
  展示所有可用的连接应用，支持按平台筛选和关键词搜索。
  点击"发起连接"进入步骤引导弹窗：选应用 → 绑店铺 → 配参数 → 设存储 → 完成创建。
-->
<template>
  <div class="marketplace">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-tabs">
        <button
          class="filter-tab"
          :class="{ active: activePlatform === '' }"
          @click="activePlatform = ''"
        >全部</button>
        <button
          v-for="p in filterPlatforms"
          :key="p.code"
          class="filter-tab"
          :class="{ active: activePlatform === p.code }"
          @click="activePlatform = p.code"
        >{{ p.name }}</button>
      </div>
      <div class="search-box">        <input
          v-model="keyword"
          type="text"
          placeholder="搜索应用名称..."
          class="search-input"
          @input="debouncedLoad"
        />
      </div>
    </div>

    <!-- 应用卡片网格 -->
    <div class="app-grid">
      <div
        v-for="(app, i) in apps"
        :key="app.id"
        class="app-card"
        :style="{ animationDelay: `${0.05 * i}s` }"
      >
        <div class="card-bar" :class="`bar-${getPlatformColor(app.platform_code)}`"></div>
        <div class="card-body">
          <div class="card-top">
            <div class="app-icon" :class="`icon-${getPlatformColor(app.platform_code)}`">
              {{ app.name[0] }}
            </div>
            <span class="platform-tag">{{ app.platform_name }}</span>
          </div>
          <h3 class="app-name">{{ app.name }}</h3>
          <p class="app-desc">{{ app.description || '暂无描述' }}</p>
          <div class="card-footer">
            <span class="app-version">v{{ app.version }}</span>
            <button class="connect-btn" @click="startConnect(app)">发起连接</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="apps.length === 0 && !loading" class="empty-state">暂无可用连接应用</div>

    <!-- ════════ 上架应用弹窗 ════════ -->
    <div v-if="publishVisible" class="modal-overlay" @click.self="publishVisible = false">
      <div class="publish-card">
        <div class="publish-header">
          <h3 class="wizard-title">添加应用</h3>
          <button class="publish-close" @click="publishVisible = false">×</button>
        </div>
        <div class="wizard-body">
          <div class="form-group">
            <label class="form-label"><span class="required-mark">*</span> 一级平台</label>
            <DcSelect
              v-model="publishPrimaryCode"
              class="form-select"
              :options="primaryPlatformOptions"
              placeholder="请选择一级平台"
            />
          </div>
          <div class="form-group">
            <label class="form-label"><span class="required-mark">*</span> 二级平台</label>
            <DcSelect
              v-model="publishSecondaryCode"
              class="form-select"
              :options="secondaryPlatformOptions"
              placeholder="请选择二级平台"
            />
          </div>
          <div class="form-group">
            <label class="form-label"><span class="required-mark">*</span> 应用选择</label>
            <DcSelect
              v-model="publishForm.adapter_key"
              class="form-select"
              :options="publishTemplateOptions"
              placeholder="请选择应用"
              @change="onSelectTemplate"
            />
            <span class="form-hint">这里展示全部已开发应用模板，请按平台对应关系选择</span>
          </div>
          <div class="form-group">
            <label class="form-label"><span class="required-mark">*</span> 版本号</label>
            <input v-model="publishForm.version" class="form-input" placeholder="1.0.0" />
          </div>
          <div class="form-group">
            <label class="form-label">应用描述</label>
            <textarea
              v-model="publishForm.description"
              class="form-input form-textarea"
              placeholder="描述应用用途与采集范围"
            />
          </div>
        </div>
        <div class="wizard-footer">
          <button class="modal-btn cancel" @click="publishVisible = false">取消</button>
          <button class="modal-btn confirm" @click="submitPublish">确认上架</button>
        </div>
      </div>
    </div>

    <!-- ════════ 发起连接 - 步骤引导弹窗 ════════ -->
    <div v-if="wizardVisible" class="modal-overlay" @click.self="wizardVisible = false">
      <div class="wizard-card">
        <!-- 步骤指示器 -->
        <div class="wizard-steps">
          <div
            v-for="(label, idx) in stepLabels"
            :key="idx"
            class="step-item"
            :class="{ active: wizardStep === idx, done: wizardStep > idx }"
          >
            <div class="step-circle">{{ wizardStep > idx ? '✓' : idx + 1 }}</div>
            <span class="step-label">{{ label }}</span>
          </div>
        </div>

        <!-- Step 0: 确认应用 -->
        <div v-if="wizardStep === 0" class="wizard-body">
          <h3 class="wizard-title">确认连接应用</h3>
          <div class="confirm-app-card">
            <div class="app-icon" :class="`icon-${getPlatformColor(selectedApp!.platform_code)}`">
              {{ selectedApp!.name[0] }}
            </div>
            <div>
              <div class="confirm-app-name">{{ selectedApp!.name }}</div>
              <div class="confirm-app-platform">{{ selectedApp!.platform_name }} · v{{ selectedApp!.version }}</div>
            </div>
          </div>
          <p class="wizard-hint">{{ selectedApp!.description }}</p>
        </div>

        <!-- Step 1: 选择店铺 -->
        <div v-if="wizardStep === 1" class="wizard-body">
          <h3 class="wizard-title">绑定店铺账号</h3>
          <div class="option-list">
            <div
              v-for="acc in availableAccounts"
              :key="acc.id"
              class="option-item"
              :class="{ selected: wizardForm.account_id === acc.id }"
              @click="wizardForm.account_id = acc.id"
            >
              <div class="option-radio" :class="{ checked: wizardForm.account_id === acc.id }"></div>
              <div>
                <div class="option-title">{{ acc.shop_name }}</div>
                <div class="option-sub">{{ acc.platform_name }} · {{ acc.username_masked }}</div>
              </div>
              <span class="health-tag" :class="getScoreClass(acc.health_score)">{{ acc.health_score }}</span>
            </div>
          </div>
          <p v-if="availableAccounts.length === 0" class="wizard-hint">该平台暂无可用账号，请先在账号管理中添加。</p>
        </div>

        <!-- Step 2: 配置参数 -->
        <div v-if="wizardStep === 2" class="wizard-body">
          <h3 class="wizard-title">任务配置</h3>
          <div class="form-group">
            <label class="form-label">任务名称</label>
            <input v-model="wizardForm.name" class="form-input" placeholder="如：旗舰店A-订单采集" />
          </div>
          <div class="form-group">
            <label class="form-label">调度表达式 (Cron)</label>
            <input v-model="wizardForm.cron_expr" class="form-input" placeholder="0 8 * * *" />
            <span class="form-hint">默认每日早 8 点执行</span>
          </div>
        </div>

        <!-- Step 3: 设置存储 -->
        <div v-if="wizardStep === 3" class="wizard-body">
          <h3 class="wizard-title">选择数据存储</h3>
          <div class="option-list">
            <div
              v-for="s in storageList"
              :key="s.id"
              class="option-item"
              :class="{ selected: wizardForm.storage_config_id === s.id }"
              @click="wizardForm.storage_config_id = s.id"
            >
              <div class="option-radio" :class="{ checked: wizardForm.storage_config_id === s.id }"></div>
              <div>
                <div class="option-title">{{ s.name }}</div>
                <div class="option-sub">{{ typeLabel(s.type) }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部按钮 -->
        <div class="wizard-footer">
          <button v-if="wizardStep > 0" class="modal-btn cancel" @click="wizardStep--">上一步</button>
          <div style="flex:1"></div>
          <button class="modal-btn cancel" @click="wizardVisible = false">取消</button>
          <button v-if="wizardStep < 3" class="modal-btn confirm" @click="nextStep">下一步</button>
          <button v-else class="modal-btn confirm" @click="submitWizard">创建任务</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'
import DcSelect from '@/components/DcSelect.vue'

const message = useMessage()

/* ── 类型 ── */
interface PlatformItem {
  id: number
  code: string
  name: string
  parent_id: number | null
  level: 1 | 2
}
interface AppItem {
  id: number; name: string; description: string | null; version: string;
  status: string; platform_code: string; platform_name: string
}
interface AccountItem {
  id: number; shop_name: string; username_masked: string; status: string;
  health_score: number; platform_code: string; platform_name: string
}
interface StorageItem { id: number; type: string; name: string; status: string }
interface AdapterItem {
  adapter_key: string
  platform_code: string
  display_name: string
  description: string
  default_version: string
  is_listed: boolean
  listed_apps: { id: number; name: string; status: string }[]
}
interface SelectOption { value: string; label: string }

/* ── 列表状态 ── */
const platforms = ref<PlatformItem[]>([])
const apps = ref<AppItem[]>([])
const activePlatform = ref('')
const keyword = ref('')
const loading = ref(false)
const availableAdapters = ref<AdapterItem[]>([])
const publishTemplateOptions = ref<SelectOption[]>([])
const publishPrimaryCode = ref('')
const publishSecondaryCode = ref('')
const publishVisible = ref(false)
const publishForm = ref({
  name: '',
  adapter_key: '',
  version: '1.0.0',
  description: '',
})

/* ── 向导状态 ── */
const wizardVisible = ref(false)
const wizardStep = ref(0)
const selectedApp = ref<AppItem | null>(null)
const availableAccounts = ref<AccountItem[]>([])
const storageList = ref<StorageItem[]>([])
const stepLabels = ['确认应用', '绑定店铺', '配置参数', '设置存储']

const wizardForm = ref({
  account_id: 0,
  name: '',
  cron_expr: '0 8 * * *',
  storage_config_id: 0,
})

/* ── 平台颜色 ── */
const platformColorMap: Record<string, string> = { taobao: 'copper', jd: 'red', pdd: 'green', douyin: 'blue' }
function getPlatformColor(code: string) { return platformColorMap[code] || 'copper' }
function getScoreClass(score: number) { return score >= 70 ? 'score-good' : score >= 30 ? 'score-warn' : 'score-bad' }
const typeLabels: Record<string, string> = { mysql: 'MySQL 数据库', feishu_bitable: '飞书多维表', dingtalk_sheet: '钉钉表格' }
function typeLabel(t: string) { return typeLabels[t] || t }

const platformByCode = computed(() => {
  const map = new Map<string, PlatformItem>()
  platforms.value.forEach((p) => map.set(p.code, p))
  return map
})

const primaryPlatforms = computed(() => platforms.value.filter((p) => p.parent_id === null))

const secondaryCandidates = computed(() => {
  const selectedPrimary = primaryPlatforms.value.find((p) => p.code === publishPrimaryCode.value)
  if (!selectedPrimary) return []
  const children = platforms.value.filter((p) => p.parent_id === selectedPrimary.id)
  return children.length > 0 ? children : [selectedPrimary]
})

const primaryPlatformOptions = computed<SelectOption[]>(() =>
  primaryPlatforms.value.map((p) => ({ value: p.code, label: p.name })),
)

const secondaryPlatformOptions = computed<SelectOption[]>(() =>
  secondaryCandidates.value.map((p) => ({ value: p.code, label: p.name })),
)

const filterPlatforms = computed(() => {
  const parentIds = new Set<number>(platforms.value.filter((p) => p.parent_id !== null).map((p) => p.parent_id as number))
  return platforms.value.filter((p) => p.level === 2 || !parentIds.has(p.id))
})

/* ── 数据加载 ── */
async function loadPlatforms() {
  const res = await axios.get('/api/v1/apps/platforms')
  platforms.value = res.data.data
}

async function loadApps() {
  loading.value = true
  const params: Record<string, string> = {}
  if (activePlatform.value) params.platform = activePlatform.value
  if (keyword.value) params.keyword = keyword.value
  const res = await axios.get('/api/v1/apps', { params })
  apps.value = res.data.data
  loading.value = false
}

async function loadAvailableAdapters() {
  const res = await axios.get('/api/v1/apps/available-adapters')
  availableAdapters.value = res.data.data
}

function openPublishModal() {
  const firstPrimary = primaryPlatforms.value[0]
  const initialPrimaryCode = firstPrimary?.code ?? ''
  const initialSecondary = (() => {
    const selectedPrimary = primaryPlatforms.value.find((p) => p.code === initialPrimaryCode)
    if (!selectedPrimary) return ''
    const children = platforms.value.filter((p) => p.parent_id === selectedPrimary.id)
    return (children[0] ?? selectedPrimary).code
  })()

  publishForm.value = {
    name: '',
    adapter_key: '',
    version: '',
    description: '',
  }
  publishPrimaryCode.value = initialPrimaryCode
  publishSecondaryCode.value = initialSecondary
  refreshTemplateOptions()
  publishVisible.value = true
}

function refreshTemplateOptions() {
  publishTemplateOptions.value = availableAdapters.value
    .map((a) => ({
      value: a.adapter_key,
      label: `${a.display_name}（${platformByCode.value.get(a.platform_code)?.name || a.platform_code}${a.is_listed ? '，已上架' : ''}）`,
    }))
}

function onSelectTemplate(adapterKey: string | number) {
  const key = String(adapterKey)
  const tpl = availableAdapters.value.find((a) => a.adapter_key === key)
  if (!tpl) return
  publishForm.value.adapter_key = tpl.adapter_key
  publishForm.value.name = tpl.display_name
  publishForm.value.description = tpl.description
  publishForm.value.version = tpl.default_version
}

async function submitPublish() {
  if (!publishPrimaryCode.value) { message.warning('请选择一级平台'); return }
  if (!publishSecondaryCode.value) { message.warning('请选择二级平台'); return }
  if (!publishForm.value.adapter_key.trim()) { message.warning('请选择应用'); return }
  const tpl = availableAdapters.value.find((a) => a.adapter_key === publishForm.value.adapter_key)
  if (!tpl) { message.warning('请选择有效应用模板'); return }
  if (tpl.is_listed) { message.warning('该应用模板已上架'); return }
  if (tpl.platform_code !== publishSecondaryCode.value) {
    const rightName = platformByCode.value.get(tpl.platform_code)?.name || tpl.platform_code
    message.warning(`应用与平台不匹配，请选择 ${rightName}`)
    return
  }
  if (!publishForm.value.name.trim()) { message.warning('应用名称为空，请重新选择模板'); return }
  if (!publishForm.value.version.trim()) { message.warning('请输入版本号'); return }

  await axios.post('/api/v1/apps', {
    platform_code: publishSecondaryCode.value,
    name: publishForm.value.name.trim(),
    adapter_key: publishForm.value.adapter_key.trim() || null,
    version: publishForm.value.version.trim(),
    description: publishForm.value.description.trim() || null,
    status: 'active',
  })

  publishVisible.value = false
  message.success('上架成功')
  await Promise.all([loadApps(), loadAvailableAdapters()])
}

let debounceTimer: ReturnType<typeof setTimeout>
function debouncedLoad() { clearTimeout(debounceTimer); debounceTimer = setTimeout(loadApps, 300) }
watch(activePlatform, loadApps)
watch(
  publishPrimaryCode,
  () => {
    const firstSecondary = secondaryCandidates.value[0]
    publishSecondaryCode.value = firstSecondary?.code ?? ''
  },
)
watch(
  publishSecondaryCode,
  () => {
    publishForm.value.adapter_key = ''
    publishForm.value.name = ''
    publishForm.value.version = ''
    publishForm.value.description = ''
  },
)

/* ── 发起连接向导 ── */
async function startConnect(app: AppItem) {
  selectedApp.value = app
  wizardStep.value = 0
  wizardForm.value = { account_id: 0, name: `${app.name}`, cron_expr: '0 8 * * *', storage_config_id: 0 }

  // 预加载账号和存储列表
  const [accRes, storRes] = await Promise.all([
    axios.get('/api/v1/accounts', { params: { platform: app.platform_code } }),
    axios.get('/api/v1/storages'),
  ])
  availableAccounts.value = accRes.data.data
  storageList.value = storRes.data.data

  // 默认选中第一项
  if (availableAccounts.value.length > 0) wizardForm.value.account_id = availableAccounts.value[0].id
  if (storageList.value.length > 0) wizardForm.value.storage_config_id = storageList.value[0].id

  wizardVisible.value = true
}

/* ── 步骤校验 ── */
function nextStep() {
  if (wizardStep.value === 1 && !wizardForm.value.account_id) {
    message.warning('请选择一个店铺账号'); return
  }
  if (wizardStep.value === 2 && !wizardForm.value.name) {
    message.warning('请输入任务名称'); return
  }
  wizardStep.value++
}

/* ── 提交创建任务 ── */
async function submitWizard() {
  if (!wizardForm.value.storage_config_id) { message.warning('请选择存储配置'); return }

  await axios.post('/api/v1/tasks', {
    app_id: selectedApp.value!.id,
    account_id: wizardForm.value.account_id,
    storage_config_id: wizardForm.value.storage_config_id,
    notification_config_id: 1, // 默认使用第一个通知配置
    name: wizardForm.value.name,
    cron_expr: wizardForm.value.cron_expr,
  })
  message.success('连接任务创建成功！')
  wizardVisible.value = false
}

onMounted(async () => {
  await Promise.all([loadPlatforms(), loadAvailableAdapters()])
  await loadApps()
})
</script>

<style scoped>
/* ── 筛选栏 ── */
.filter-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; gap: 16px; }
.filter-tabs { display: flex; gap: 6px; }
.filter-tab {
  padding: 6px 16px; border-radius: var(--radius-pill); font-size: 13px; font-weight: 500;
  background: var(--bg-card); border: 1px solid var(--border-light); color: var(--text-secondary);
  cursor: pointer; transition: all 0.2s; font-family: var(--font-body);
}
.filter-tab:hover { border-color: var(--accent-copper-light); color: var(--text-primary); }
.filter-tab.active { background: var(--accent-copper-bg); border-color: var(--accent-copper-light); color: var(--accent-copper); }
.search-input {
  padding: 8px 16px; border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--bg-card); font-size: 13px; font-family: var(--font-body); color: var(--text-primary);
  width: 220px; outline: none; transition: border-color 0.2s;
}
.search-box { display: flex; align-items: center; gap: 10px; }
.publish-btn {
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--accent-copper-light);
  background: var(--accent-copper-bg);
  color: var(--accent-copper);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.publish-btn:hover {
  border-color: var(--accent-copper);
  box-shadow: 0 2px 8px rgba(200,149,108,0.2);
}
.search-input:focus { border-color: var(--accent-copper); }
.search-input::placeholder { color: var(--text-tertiary); }

/* ── 卡片网格 ── */
.app-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 18px; }
.app-card {
  background: var(--bg-card); border-radius: var(--radius-md); border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm); overflow: hidden; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  opacity: 0; transform: translateY(16px); animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.app-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); border-color: var(--accent-copper-light); }
.card-bar { height: 3px; }
.bar-copper { background: linear-gradient(90deg, var(--accent-copper), var(--accent-copper-light)); }
.bar-red { background: linear-gradient(90deg, var(--accent-red), var(--accent-red-light)); }
.bar-green { background: linear-gradient(90deg, var(--accent-green), var(--accent-green-light)); }
.bar-blue { background: linear-gradient(90deg, var(--accent-blue), var(--accent-blue-light)); }
.card-body { padding: 20px; }
.card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.app-icon {
  width: 40px; height: 40px; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 600;
}
.icon-copper { background: var(--accent-copper-bg); color: var(--accent-copper); }
.icon-red { background: var(--accent-red-bg); color: var(--accent-red); }
.icon-green { background: var(--accent-green-bg); color: var(--accent-green); }
.icon-blue { background: var(--accent-blue-bg); color: var(--accent-blue); }
.platform-tag { padding: 3px 10px; border-radius: var(--radius-pill); font-size: 11px; font-weight: 500; background: var(--bg-subtle); color: var(--text-secondary); }
.app-name { font-family: var(--font-display); font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.app-desc { font-size: 12.5px; color: var(--text-tertiary); line-height: 1.5; margin-bottom: 16px; min-height: 38px; }
.card-footer { display: flex; align-items: center; justify-content: space-between; }
.app-version { font-family: var(--font-mono); font-size: 11.5px; color: var(--text-tertiary); }
.connect-btn {
  padding: 6px 16px; border-radius: var(--radius-sm); font-size: 12.5px; font-weight: 500;
  background: linear-gradient(135deg, var(--accent-copper), #B88560); color: var(--text-inverse);
  border: none; cursor: pointer; transition: all 0.2s; font-family: var(--font-body);
}
.connect-btn:hover { box-shadow: 0 2px 8px rgba(200,149,108,0.3); transform: translateY(-1px); }
.empty-state { text-align: center; padding: 60px 0; color: var(--text-tertiary); font-size: 14px; }

/* ════════ 步骤引导弹窗 ════════ */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(45,42,38,0.3); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.wizard-card {
  background: var(--bg-card); border-radius: var(--radius-lg); padding: 0;
  width: 520px; max-width: 92vw; box-shadow: var(--shadow-lg);
  animation: fadeUp 0.3s cubic-bezier(0.16, 1, 0.3, 1); overflow: hidden;
}
.publish-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  width: 520px;
  max-width: 92vw;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}
.publish-header {
  padding: 16px 28px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.publish-close {
  width: 28px;
  height: 28px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--bg-card);
  color: var(--text-tertiary);
  cursor: pointer;
  line-height: 1;
  font-size: 16px;
}
.publish-close:hover {
  color: var(--text-primary);
  border-color: var(--text-tertiary);
}
.required-mark {
  color: var(--accent-red);
  margin-right: 2px;
}
.form-textarea {
  min-height: 88px;
  resize: vertical;
}

/* 步骤指示器 */
.wizard-steps {
  display: flex; padding: 20px 28px; gap: 4px;
  background: var(--bg-subtle); border-bottom: 1px solid var(--border-light);
}
.step-item {
  flex: 1; display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--text-tertiary); transition: color 0.2s;
}
.step-item.active { color: var(--accent-copper); font-weight: 600; }
.step-item.done { color: var(--accent-green); }
.step-circle {
  width: 24px; height: 24px; border-radius: 50%; font-size: 11px; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
  border: 2px solid var(--border); color: var(--text-tertiary); background: var(--bg-card);
  transition: all 0.2s; flex-shrink: 0;
}
.step-item.active .step-circle { border-color: var(--accent-copper); color: var(--accent-copper); background: var(--accent-copper-bg); }
.step-item.done .step-circle { border-color: var(--accent-green); color: white; background: var(--accent-green); }
.step-label { white-space: nowrap; }

/* 向导内容 */
.wizard-body { padding: 16px 20px; min-height: 200px; max-height: 62vh; overflow-y: auto; }
.wizard-title { font-family: var(--font-display); font-size: 20px; font-weight: 600; color: var(--text-primary); margin: 0; }
.wizard-hint { font-size: 12.5px; color: var(--text-tertiary); line-height: 1.6; margin-top: 12px; }

/* 确认应用卡片 */
.confirm-app-card { display: flex; align-items: center; gap: 14px; padding: 14px 16px; background: var(--bg-subtle); border-radius: var(--radius-sm); }
.confirm-app-name { font-weight: 600; font-size: 14px; color: var(--text-primary); }
.confirm-app-platform { font-size: 12px; color: var(--text-tertiary); margin-top: 2px; }

/* 选项列表（店铺/存储） */
.option-list { display: flex; flex-direction: column; gap: 8px; }
.option-item {
  display: flex; align-items: center; gap: 12px; padding: 12px 14px;
  border: 1px solid var(--border-light); border-radius: var(--radius-sm);
  cursor: pointer; transition: all 0.15s;
}
.option-item:hover { border-color: var(--accent-copper-light); background: var(--bg-hover); }
.option-item.selected { border-color: var(--accent-copper); background: var(--accent-copper-bg); }
.option-radio {
  width: 16px; height: 16px; border-radius: 50%; border: 2px solid var(--border);
  flex-shrink: 0; transition: all 0.15s; position: relative;
}
.option-radio.checked { border-color: var(--accent-copper); }
.option-radio.checked::after {
  content: ''; position: absolute; inset: 3px; border-radius: 50%; background: var(--accent-copper);
}
.option-title { font-size: 13.5px; font-weight: 500; color: var(--text-primary); }
.option-sub { font-size: 11.5px; color: var(--text-tertiary); margin-top: 2px; }
.health-tag { margin-left: auto; font-family: var(--font-mono); font-size: 12px; font-weight: 600; }
.score-good { color: var(--accent-green); }
.score-warn { color: var(--accent-amber); }
.score-bad { color: var(--accent-red); }

/* 表单 */
.form-group { margin-bottom: 16px; }
.form-label { display: block; font-size: 12.5px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px; }
.form-input {
  width: 100%; padding: 9px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--bg-base); font-size: 13px; font-family: var(--font-body); color: var(--text-primary); outline: none;
}
.form-select {
  width: 100%;
  display: block;
}
:deep(.form-select .dc-select) {
  width: 100%;
  display: flex;
}
.form-input:focus { border-color: var(--accent-copper); }
.form-hint { font-size: 11px; color: var(--text-tertiary); margin-top: 4px; display: block; }

/* 底部按钮 */
.wizard-footer {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 28px; border-top: 1px solid var(--border-light);
}
.modal-btn {
  padding: 8px 20px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500;
  cursor: pointer; font-family: var(--font-body); transition: all 0.2s;
}
.modal-btn.cancel { background: var(--bg-subtle); border: 1px solid var(--border); color: var(--text-secondary); }
.modal-btn.cancel:hover { border-color: var(--text-tertiary); }
.modal-btn.confirm { background: linear-gradient(135deg, var(--accent-copper), #B88560); border: none; color: var(--text-inverse); }
.modal-btn.confirm:hover { box-shadow: 0 2px 8px rgba(200,149,108,0.3); }
</style>

