<template>
  <div class="workbench-page">
    <div class="toolbar">
      <div class="left">
        <input v-model="filename" class="name-input" placeholder="文件名，如：douyin/new_adapter.py" />
        <input v-model="previewUrl" class="name-input wide" placeholder="预览网址，如：https://example.com" />
      </div>
      <div class="right">
        <button class="ghost-btn" @click="fillTemplate">填充模板</button>
        <button class="ghost-btn" @click="copyCode">复制代码</button>
        <button class="primary-btn" @click="downloadPy">下载 .py</button>
      </div>
    </div>

    <div class="main-grid">
      <section class="card editor-panel">
        <div class="panel-title">代码编辑区（DrissionPage）</div>
        <textarea v-model="code" class="editor" spellcheck="false" />
      </section>

      <section class="card web-preview">
        <div class="panel-title">页面预览</div>
        <iframe class="preview-frame" :src="safePreviewUrl" />
      </section>
    </div>

    <section class="card ops-preview">
      <div class="panel-title">实时操作预览（由代码解析）</div>
      <div v-if="operations.length === 0" class="empty">暂无可识别操作，请编写 `page.get/click/input/wait/sleep` 语句。</div>
      <div v-for="(op, index) in operations" :key="`${op.line}-${index}`" class="op-row">
        <span class="op-index">{{ index + 1 }}</span>
        <span class="op-type">{{ op.type }}</span>
        <span class="op-detail">{{ op.detail }}</span>
        <span class="op-line">L{{ op.line }}</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * 页面用途：开发者代码工作台（DrissionPage）。
 * 核心职责：提供代码编辑、页面预览、实时操作解析、草稿保存与 Python 导出。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'

interface ParsedOp {
  type: string
  detail: string
  line: number
}

const message = useMessage()
const storageKey = 'dc_adapter_code_workbench'
const filename = ref('new_adapter.py')
const previewUrl = ref('https://example.com')
const code = ref('')

const template = `"""
文件用途：DrissionPage 自动化适配器示例。
说明：补齐登录、采集与异常处理逻辑后，再注册并发版。
"""

from infrastructure.connectors.base.adapter import BaseAdapter, AdapterResult


class NewAdapter(BaseAdapter):
    """适配器职责：执行网页自动化并返回标准结果。"""

    adapter_key = "douyin.new_adapter"

    async def execute(self, credentials: dict, params: dict | None = None) -> AdapterResult:
        # 示例动作（会在右侧实时操作预览中展示）
        page.get("https://example.com")
        page.ele("#username").input(credentials.get("username", ""))
        page.ele("#password").input(credentials.get("password", ""))
        page.ele("#login-btn").click()
        page.wait.ele_displayed("text:登录成功", timeout=15)
        sleep(1)

        data_rows = []
        return AdapterResult(success=True, rows_count=len(data_rows), data=data_rows)
`

const safePreviewUrl = computed(() => {
  const value = previewUrl.value.trim()
  if (!value) return 'about:blank'
  if (value.startsWith('http://') || value.startsWith('https://')) return value
  return `https://${value}`
})

/** 基于常见 DrissionPage 语句做轻量解析，实时展示“将执行什么”。 */
const operations = computed<ParsedOp[]>(() => {
  const rows = code.value.split('\n')
  const result: ParsedOp[] = []
  rows.forEach((raw, idx) => {
    const line = raw.trim()
    if (!line || line.startsWith('#')) return

    const getMatch = line.match(/page\.get\((.+)\)/)
    if (getMatch) {
      result.push({ type: '打开网页', detail: getMatch[1], line: idx + 1 })
      return
    }

    const inputMatch = line.match(/\.input\((.+)\)/)
    if (inputMatch) {
      result.push({ type: '输入文本', detail: inputMatch[1], line: idx + 1 })
      return
    }

    if (line.includes('.click(')) {
      result.push({ type: '点击元素', detail: line, line: idx + 1 })
      return
    }

    const waitMatch = line.match(/wait\.[a-zA-Z_]+\((.+)\)/)
    if (waitMatch) {
      result.push({ type: '等待条件', detail: waitMatch[1], line: idx + 1 })
      return
    }

    const sleepMatch = line.match(/sleep\((.+)\)/)
    if (sleepMatch) {
      result.push({ type: '延时', detail: `${sleepMatch[1]} 秒`, line: idx + 1 })
    }
  })
  return result
})

function fillTemplate() {
  code.value = template
  message.success('模板已填充')
}

async function copyCode() {
  await navigator.clipboard.writeText(code.value)
  message.success('代码已复制')
}

function downloadPy() {
  const blob = new Blob([code.value], { type: 'text/x-python' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = (filename.value || 'new_adapter.py').split('/').pop() || 'new_adapter.py'
  a.click()
  URL.revokeObjectURL(url)
  message.success('已下载 Python 文件')
}

watch([filename, previewUrl, code], () => {
  localStorage.setItem(
    storageKey,
    JSON.stringify({
      filename: filename.value,
      preview_url: previewUrl.value,
      code: code.value,
    }),
  )
}, { deep: true })

onMounted(() => {
  const raw = localStorage.getItem(storageKey)
  if (!raw) {
    fillTemplate()
    return
  }
  try {
    const draft = JSON.parse(raw) as { filename?: string, preview_url?: string, code?: string }
    filename.value = draft.filename || 'new_adapter.py'
    previewUrl.value = draft.preview_url || 'https://example.com'
    code.value = draft.code || template
  } catch {
    fillTemplate()
  }
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 12px; }
.left { display: flex; gap: 8px; flex: 1; min-width: 0; }
.right { display: flex; gap: 8px; }
.name-input {
  width: 240px;
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-base);
  color: var(--text-primary);
}
.name-input.wide { width: 360px; }

.main-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 12px; margin-bottom: 12px; }
.card { background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-md); }
.panel-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); padding: 10px 12px; border-bottom: 1px solid var(--border-light); }

.editor-panel { min-height: calc(100vh - 210px); overflow: hidden; }
.editor {
  width: 100%;
  height: calc(100vh - 255px);
  min-height: 460px;
  border: none;
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

.web-preview { overflow: hidden; }
.preview-frame {
  width: 100%;
  height: calc(100vh - 255px);
  min-height: 460px;
  border: 0;
  background: #fff;
}

.ops-preview { min-height: 220px; }
.empty { padding: 12px; color: var(--text-tertiary); font-size: 12.5px; }
.op-row {
  display: grid;
  grid-template-columns: 30px 78px 1fr auto;
  gap: 8px;
  padding: 8px 12px;
  border-top: 1px solid var(--border-light);
  font-size: 12.5px;
}
.op-index { color: var(--text-tertiary); }
.op-type { color: var(--accent-copper); font-weight: 600; }
.op-detail { color: var(--text-primary); word-break: break-all; }
.op-line { color: var(--text-tertiary); font-family: var(--font-mono); }

.primary-btn {
  padding: 9px 14px;
  border: none;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--accent-copper), #B88560);
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

@media (max-width: 1180px) {
  .main-grid { grid-template-columns: 1fr; }
  .left { flex-direction: column; }
  .name-input, .name-input.wide { width: 100%; }
}
</style>
