<!--
  页面用途：
  1. 提供“应用编排（登录 + 取数 + 上传）”的纯代码工作台。
  2. 左侧编写三类代码：登录指令、取数指令、适配器编排。
  3. 右侧完成参数测试运行、浏览器预览入口与结果日志查看。
-->
<template>
  <div class="workbench-page">
    <div class="toolbar">
      <div class="toolbar-left">
        <input v-model="platformCode" class="name-input short" placeholder="一级平台，如 douyin" />
        <input v-model="appSlug" class="name-input short" placeholder="应用标识，如 product_overview" />
        <input v-model="previewUrl" class="name-input wide" placeholder="预览地址，如 https://www.baidu.com" />
      </div>
      <div class="toolbar-right">
        <button class="ghost-btn" @click="generateScaffold">生成三件套</button>
        <button class="ghost-btn" @click="saveCurrentFile" :disabled="!activeFile">保存当前</button>
        <button class="primary-btn" @click="runTest">测试运行</button>
      </div>
    </div>

    <div class="main-grid">
      <section class="card editor-panel">
        <div class="panel-title">代码编辑区（登录 / 取数 / 适配器编排）</div>
        <div class="part-tabs">
          <button
            v-for="part in partOptions"
            :key="part.key"
            class="part-tab"
            :class="{ active: activePart === part.key }"
            @click="activePart = part.key"
          >
            <span>{{ part.label }}</span>
            <span v-if="parts[part.key].dirty" class="dirty-dot"></span>
          </button>
        </div>
        <div class="path-row">
          <span class="label">当前文件：</span>
          <span class="path">{{ activeFile?.relativePath || '未选择' }}</span>
        </div>
        <textarea
          v-model="activeCode"
          class="editor"
          spellcheck="false"
          placeholder="请先点击“生成三件套”，或从“我开发的指令”进入已有文件"
        />
      </section>

      <section class="card side-panel">
        <div class="panel-title">运行参数与浏览器预览</div>
        <div class="form-grid">
          <label class="field">
            <span>账号</span>
            <input v-model="runUsername" class="field-input" placeholder="测试账号（可选）" />
          </label>
          <label class="field">
            <span>密码</span>
            <input
              v-model="runPassword"
              class="field-input"
              type="password"
              placeholder="测试密码（可选）"
            />
          </label>
          <label class="field">
            <span>默认下载天数</span>
            <input v-model.number="defaultDownloadDays" class="field-input" type="number" min="1" />
          </label>
          <label class="field checkbox-field">
            <input v-model="realBrowser" type="checkbox" />
            <span>真实浏览器模式（real_browser）</span>
          </label>
          <label class="field">
            <span>关键词（demo）</span>
            <input v-model="runKeyword" class="field-input" placeholder="如：你好" />
          </label>
        </div>

        <div class="preview-head">
          <div class="preview-title">页面预览</div>
          <a class="preview-link" :href="safePreviewUrl" target="_blank" rel="noreferrer">新窗口打开</a>
        </div>
        <iframe class="preview-frame" :src="safePreviewUrl" />
      </section>
    </div>

    <section class="card result-panel">
      <div class="panel-title">测试结果面板</div>
      <div class="result-summary">
        <span>状态：<b :class="runResult?.success ? 'ok' : 'editing'">{{ runResultStatus }}</b></span>
        <span>耗时：{{ runResult?.duration_ms ?? '-' }} ms</span>
        <span>条数：{{ runResult?.rows_count ?? '-' }}</span>
        <span>日期范围：{{ runResult?.start_date ?? '-' }} ~ {{ runResult?.end_date ?? '-' }}</span>
      </div>
      <div class="result-logs">
        <div class="log-title">执行日志</div>
        <div v-if="!runResult || runResult.logs.length === 0" class="empty">暂无日志</div>
        <div v-for="(log, idx) in runResult?.logs || []" :key="`${log.time}-${idx}`" class="log-row">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
      <div class="result-data">
        <div class="log-title">返回数据预览（前 20 条）</div>
        <pre class="result-json">{{ runResult ? jsonPreview(runResult.data_preview) : '[]' }}</pre>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * 工作台核心逻辑：
 * 1. 维护“登录指令 / 取数指令 / 适配器编排”三类文件状态。
 * 2. 支持生成脚手架、读取已有文件、保存代码。
 * 3. 统一测试运行入口，复用后端 workbench run 接口。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { useRoute } from 'vue-router'
import axios from 'axios'

type PartKey = 'adapter' | 'login' | 'collect'

interface PartFile {
  relativePath: string
  code: string
  dirty: boolean
}

interface RunLog {
  time: string
  message: string
}

interface RunResult {
  success: boolean
  rows_count: number
  duration_ms: number
  start_date: string
  end_date: string
  logs: RunLog[]
  data_preview: Array<Record<string, unknown>>
}

const message = useMessage()
const route = useRoute()

const platformCode = ref('douyin')
const appSlug = ref('new_app')
const previewUrl = ref('https://www.baidu.com')
const activePart = ref<PartKey>('adapter')
const loadingRun = ref(false)

const runUsername = ref('')
const runPassword = ref('')
const defaultDownloadDays = ref(1)
const realBrowser = ref(true)
const runKeyword = ref('你好')

const partOptions: Array<{ key: PartKey; label: string }> = [
  { key: 'adapter', label: '应用编排（适配器）' },
  { key: 'login', label: '登录指令' },
  { key: 'collect', label: '取数指令' },
]

const parts = reactive<Record<PartKey, PartFile>>({
  adapter: { relativePath: '', code: '', dirty: false },
  login: { relativePath: '', code: '', dirty: false },
  collect: { relativePath: '', code: '', dirty: false },
})

const runResult = ref<RunResult | null>(null)

const safePreviewUrl = computed(() => {
  const value = previewUrl.value.trim()
  if (!value) return 'about:blank'
  if (value.startsWith('http://') || value.startsWith('https://')) return value
  return `https://${value}`
})

const activeFile = computed(() => parts[activePart.value])

const activeCode = computed({
  get: () => activeFile.value?.code || '',
  set: (val: string) => {
    const file = activeFile.value
    if (!file) return
    file.code = val
    file.dirty = true
  },
})

const runResultStatus = computed(() => {
  if (loadingRun.value) return '运行中'
  if (!runResult.value) return '未运行'
  return runResult.value.success ? '成功' : '失败'
})

function inferFromRelativePath(relativePath: string): void {
  const normalized = relativePath.replace(/\\/g, '/')
  const idx = normalized.lastIndexOf('/')
  if (idx <= 0) return
  const maybePlatform = normalized.slice(0, idx).split('/').pop() || ''
  const filename = normalized.slice(idx + 1).replace('.py', '')
  if (maybePlatform && !maybePlatform.includes('instructions')) {
    platformCode.value = maybePlatform
    appSlug.value = filename.replace(/_login$|_collect$/, '')
  }
}

function fillPathsByConvention(): void {
  const platform = platformCode.value.trim().toLowerCase()
  const slug = appSlug.value.trim().toLowerCase().replace(/-/g, '_')
  parts.adapter.relativePath = `${platform}/${slug}.py`
  parts.login.relativePath = `login_instructions/${platform}/${slug}_login.py`
  parts.collect.relativePath = `collect_instructions/${platform}/${slug}_collect.py`
}

async function loadFile(part: PartKey): Promise<void> {
  const path = parts[part].relativePath
  if (!path) return
  try {
    const res = await axios.get('/api/v1/dev/instructions/content', {
      params: { relative_path: path },
    })
    parts[part].code = res.data.data?.content || ''
    parts[part].dirty = false
  } catch {
    parts[part].code = ''
  }
}

async function generateScaffold(): Promise<void> {
  const platform = platformCode.value.trim().toLowerCase()
  const slug = appSlug.value.trim().toLowerCase().replace(/-/g, '_')
  if (!platform || !slug) {
    message.warning('请先输入一级平台和应用标识')
    return
  }
  await axios.post('/api/v1/dev/instructions/workbench/scaffold', {
    platform_code: platform,
    app_slug: slug,
    overwrite: false,
  })
  fillPathsByConvention()
  await Promise.all([loadFile('adapter'), loadFile('login'), loadFile('collect')])
  activePart.value = 'adapter'
  message.success('已生成并加载应用三件套')
}

/**
 * 保存单个文件内容到后端。
 */
async function savePart(part: PartKey): Promise<void> {
  const file = parts[part]
  if (!file.relativePath) return
  await axios.put('/api/v1/dev/instructions/content', {
    relative_path: file.relativePath,
    content: file.code,
  })
  file.dirty = false
}

async function saveCurrentFile(): Promise<void> {
  if (!activeFile.value?.relativePath) {
    message.warning('当前没有可保存文件')
    return
  }
  await savePart(activePart.value)
  message.success('当前文件已保存')
}

async function saveAllDirty(): Promise<void> {
  const dirtyParts = partOptions
    .map((p) => p.key)
    .filter((key) => parts[key].relativePath && parts[key].dirty)
  for (const part of dirtyParts) {
    await savePart(part)
  }
}

/**
 * 触发工作台测试运行：
 * 1. 先保存脏文件，确保后端加载最新代码。
 * 2. 再按适配器文件路径执行 run 接口。
 */
async function runTest(): Promise<void> {
  if (!parts.adapter.relativePath) {
    message.warning('请先生成或加载适配器文件')
    return
  }
  loadingRun.value = true
  try {
    await saveAllDirty()
    const res = await axios.post('/api/v1/dev/instructions/workbench/run', {
      relative_path: parts.adapter.relativePath,
      credentials: {
        username: runUsername.value,
        password: runPassword.value,
      },
      app_params: {
        default_download_days: defaultDownloadDays.value,
        real_browser: realBrowser.value,
        keyword: runKeyword.value || '你好',
      },
      extra: {
        company_name: 'dc_connection',
        platform_code: platformCode.value,
        account_name: runUsername.value || 'workbench',
      },
    })
    const data = res.data.data || {}
    runResult.value = {
      success: !!data.success,
      rows_count: Number(data.rows_count || 0),
      duration_ms: Number(data.duration_ms || 0),
      start_date: String(data.start_date || ''),
      end_date: String(data.end_date || ''),
      logs: (data.logs || []) as RunLog[],
      data_preview: (data.data_preview || []) as Array<Record<string, unknown>>,
    }
    if (runResult.value.success) {
      message.success('测试运行完成')
    } else {
      message.error(data.error_message || '测试运行失败')
    }
  } catch (error: any) {
    const msg = error?.response?.data?.message || '测试运行失败'
    message.error(msg)
  } finally {
    loadingRun.value = false
  }
}

function jsonPreview(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

onMounted(async () => {
  const queryPath = String(route.query.relative_path || '').trim()
  if (queryPath) {
    inferFromRelativePath(queryPath)
    fillPathsByConvention()
    parts.adapter.relativePath = queryPath
    await Promise.all([loadFile('adapter'), loadFile('login'), loadFile('collect')])
    activePart.value = 'adapter'
    return
  }
  fillPathsByConvention()
})
</script>

<style scoped>
.workbench-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.toolbar-left {
  display: flex;
  gap: 8px;
  flex: 1;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.name-input {
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-base);
  color: var(--text-primary);
}

.name-input.short {
  width: 210px;
}

.name-input.wide {
  flex: 1;
  min-width: 280px;
}

.main-grid {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 12px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-light);
}

.part-tabs {
  display: flex;
  gap: 8px;
  padding: 10px 12px 0;
}

.part-tab {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  color: var(--text-secondary);
  padding: 7px 10px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.part-tab.active {
  border-color: var(--accent-copper);
  background: var(--accent-copper-bg);
  color: var(--text-primary);
}

.dirty-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #e08b43;
}

.path-row {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 12px 0;
}

.path-row .label {
  color: var(--text-tertiary);
  font-size: 12px;
}

.path-row .path {
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
}

.editor {
  width: calc(100% - 24px);
  margin: 10px 12px 12px;
  height: calc(100vh - 355px);
  min-height: 420px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  resize: none;
  outline: none;
  padding: 12px;
  box-sizing: border-box;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
  background: #fffdf9;
  color: #2d2a26;
}

.side-panel {
  overflow: hidden;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 10px 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}

.field-input {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-base);
  color: var(--text-primary);
  padding: 8px 10px;
}

.checkbox-field {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  grid-column: 1 / -1;
}

.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px 8px;
}

.preview-title {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.preview-link {
  color: var(--accent-copper);
  text-decoration: none;
  font-size: 12px;
}

.preview-frame {
  width: calc(100% - 24px);
  margin: 0 12px 12px;
  height: 330px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: #fff;
}

.result-panel {
  min-height: 240px;
}

.result-summary {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-light);
  font-size: 12.5px;
  color: var(--text-secondary);
}

.result-logs,
.result-data {
  padding: 10px 12px;
}

.log-title {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}

.log-row {
  display: grid;
  grid-template-columns: 170px 1fr;
  gap: 8px;
  padding: 6px 0;
  border-top: 1px solid var(--border-light);
  font-size: 12px;
}

.log-time {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.log-message {
  color: var(--text-primary);
}

.result-json {
  margin: 0;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: #faf8f4;
  padding: 10px;
  max-height: 240px;
  overflow: auto;
  font-family: var(--font-mono);
  font-size: 12px;
  color: #2d2a26;
}

.primary-btn {
  padding: 9px 14px;
  border: none;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--accent-copper), #b88560);
  color: var(--text-inverse);
  cursor: pointer;
}

.ghost-btn {
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  color: var(--text-secondary);
  cursor: pointer;
}

.ghost-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ok {
  color: #2b8a3e;
}

.editing {
  color: #b45e3b;
}

.empty {
  color: var(--text-tertiary);
  font-size: 12px;
}

@media (max-width: 1200px) {
  .main-grid {
    grid-template-columns: 1fr;
  }

  .editor {
    min-height: 360px;
    height: 360px;
  }
}

@media (max-width: 980px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left {
    flex-direction: column;
  }

  .name-input.short,
  .name-input.wide {
    width: 100%;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
