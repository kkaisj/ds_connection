<!--
  页面用途：
  1. 以 IDE 资源管理器风格展示“我开发的指令”目录树。
  2. 支持多文件标签页打开、切换与关闭。
  3. 按扩展名智能匹配文件图标（py/json/md/yaml/sql 等）并展示代码详情。
-->
<template>
  <div class="instructions-page">
    <div class="toolbar">
      <div class="title-wrap">
        <h2>我开发的指令</h2>
        <span class="count">共 {{ rows.length }} 条</span>
      </div>
      <div class="search-wrap">
        <DcSelect v-model="statusFilter" class="filter-select" :options="statusFilterOptions" />
        <DcSelect v-model="sortOrder" class="filter-select" :options="sortOrderOptions" />
        <input
          v-model="keyword"
          class="search-input"
          placeholder="搜索名称 / 路径..."
          @input="loadRows"
        />
      </div>
    </div>

    <div class="main-grid">
      <section class="explorer">
        <div class="explorer-head">EXPLORER</div>
        <div class="tree-list">
          <div
            v-for="node in visibleNodes"
            :key="node.path"
            class="tree-row"
            :class="{ active: selectedPath === node.path, dir: node.isDir }"
            :style="{ paddingLeft: `${12 + node.depth * 16}px` }"
            @click="onNodeClick(node)"
          >
            <span class="caret">
              <template v-if="node.isDir">{{ isExpanded(node.path) ? '▾' : '▸' }}</template>
            </span>
            <span class="file-icon" :class="iconClass(node)" aria-hidden="true">
              <span v-if="!node.isDir" class="file-corner"></span>
              <span v-if="fileExt(node.name) === 'PY'" class="py-mark"></span>
            </span>
            <span class="tree-name">{{ node.name }}</span>
            <span v-if="!node.isDir" class="ext-badge" :class="extClass(node.name)">
              {{ fileExt(node.name) }}
            </span>
            <span
              v-if="!node.isDir && node.item"
              class="status-pill-mini"
              :class="statusClass(node.item.status)"
            >
              {{ shortStatus(node.item.status) }}
            </span>
          </div>
          <div v-if="visibleNodes.length === 0" class="empty-cell">暂无可展示指令</div>
        </div>
      </section>

      <section class="editor">
        <div class="editor-head">
          <div class="tabs-wrap">
            <button
              v-for="tab in openTabs"
              :key="tab.relativePath"
              class="tab"
              :class="{ active: activeTabPath === tab.relativePath }"
              @click="activateTab(tab.relativePath)"
            >
              <span class="tab-icon" :class="iconClassByName(tab.name)"></span>
              <span class="tab-title">{{ tab.name }}</span>
              <span
                class="tab-close"
                title="关闭"
                @click.stop="closeTab(tab.relativePath)"
              >
                ×
              </span>
            </button>
            <div v-if="openTabs.length === 0" class="tab-empty">未打开文件</div>
          </div>

          <div class="head-actions">
            <button class="ghost-btn" @click="openInWorkbench" :disabled="!activeTab">在工作台打开</button>
            <button class="ghost-btn" @click="copyCode" :disabled="!activeTab">复制代码</button>
          </div>
        </div>

        <div v-if="activeTab" class="meta-bar">
          <span>类型：{{ kindText[activeTab.item.kind] || activeTab.item.kind }}</span>
          <span>状态：<b :class="statusClass(activeTab.item.status)">{{ activeTab.item.status }}</b></span>
          <span>更新时间：{{ formatTime(activeTab.item.updated_at) }}</span>
          <span class="mono">路径：{{ activeTab.item.relative_path }}</span>
        </div>

        <div class="code-panel">
          <template v-if="activeTab">
            <div v-if="activeTab.loading" class="code-placeholder">加载中...</div>
            <div v-else-if="activeTab.error" class="code-placeholder">{{ activeTab.error }}</div>
            <div v-else class="code-lines">
              <div v-for="(line, idx) in activeCodeLines" :key="idx" class="code-line">
                <span class="line-no">{{ idx + 1 }}</span>
                <span class="line-text">{{ line || ' ' }}</span>
              </div>
            </div>
          </template>
          <div v-else class="code-placeholder">请在左侧选择一个文件</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 核心逻辑说明：
 * 1. 拉取后端文件清单并构建目录树展示。
 * 2. 维护多文件标签页状态（打开、激活、关闭）。
 * 3. 按需拉取代码内容并在右侧编辑器区展示。
 */
import { computed, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { useRouter } from 'vue-router'
import axios from 'axios'
import DcSelect from '@/components/DcSelect.vue'

interface InstructionRow {
  name: string
  kind: string
  status: string
  updated_at: string
  relative_path: string
  adapter_key: string | null
}

interface TreeNode {
  name: string
  path: string
  isDir: boolean
  children: TreeNode[]
  item: InstructionRow | null
}

interface FlatNode {
  name: string
  path: string
  isDir: boolean
  depth: number
  item: InstructionRow | null
}

interface OpenTab {
  name: string
  relativePath: string
  item: InstructionRow
  code: string
  loading: boolean
  error: string
}

const message = useMessage()
const router = useRouter()

const keyword = ref('')
const rows = ref<InstructionRow[]>([])
const statusFilter = ref('')
const sortOrder = ref<'asc' | 'desc'>('desc')
const expandedDirs = ref<Set<string>>(new Set())
const selectedPath = ref('')
const openTabs = ref<OpenTab[]>([])
const activeTabPath = ref('')

const kindText: Record<string, string> = {
  adapter: '应用适配器',
  login_instruction: '登录指令',
  collect_instruction: '取数指令',
}

const statusFilterOptions = [
  { value: '', label: '全部状态' },
  { value: '已发版', label: '已发版' },
  { value: '已注册', label: '已注册' },
  { value: '编辑中', label: '编辑中' },
]

const sortOrderOptions = [
  { value: 'desc', label: '更新时间 ↓' },
  { value: 'asc', label: '更新时间 ↑' },
]

const displayRows = computed(() => {
  const filtered = rows.value.filter((item) => !statusFilter.value || item.status === statusFilter.value)
  return filtered.slice().sort((a, b) => {
    const ta = new Date(a.updated_at).getTime()
    const tb = new Date(b.updated_at).getTime()
    return sortOrder.value === 'asc' ? ta - tb : tb - ta
  })
})

const activeTab = computed<OpenTab | null>(() => {
  if (!activeTabPath.value) return null
  return openTabs.value.find((tab) => tab.relativePath === activeTabPath.value) || null
})

const activeCodeLines = computed(() => {
  const code = activeTab.value?.code ?? ''
  return code.split('\n')
})

/**
 * 根据后端路径构建目录树，用于左侧 Explorer 展示。
 */
const treeRoot = computed<TreeNode>(() => {
  const root: TreeNode = {
    name: 'root',
    path: '',
    isDir: true,
    children: [],
    item: null,
  }

  for (const item of displayRows.value) {
    const parts = item.relative_path.split('/')
    let cursor = root
    let fullPath = ''
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      fullPath = fullPath ? `${fullPath}/${part}` : part
      const isLeaf = i === parts.length - 1
      let node = cursor.children.find((child) => child.name === part && child.isDir !== isLeaf)
      if (!node) {
        node = {
          name: part,
          path: fullPath,
          isDir: !isLeaf,
          children: [],
          item: isLeaf ? item : null,
        }
        cursor.children.push(node)
      } else if (isLeaf) {
        node.item = item
      }
      cursor = node
    }
  }

  const sortNode = (node: TreeNode): void => {
    node.children.sort((a, b) => {
      if (a.isDir !== b.isDir) return a.isDir ? -1 : 1
      return a.name.localeCompare(b.name, 'zh-Hans-CN')
    })
    node.children.forEach(sortNode)
  }
  sortNode(root)
  return root
})

const visibleNodes = computed<FlatNode[]>(() => {
  const out: FlatNode[] = []
  const dfs = (node: TreeNode, depth: number): void => {
    for (const child of node.children) {
      out.push({
        name: child.name,
        path: child.path,
        isDir: child.isDir,
        depth,
        item: child.item,
      })
      if (child.isDir && isExpanded(child.path)) {
        dfs(child, depth + 1)
      }
    }
  }
  dfs(treeRoot.value, 0)
  return out
})

function isExpanded(path: string): boolean {
  return expandedDirs.value.has(path)
}

function toggleDir(path: string): void {
  const next = new Set(expandedDirs.value)
  if (next.has(path)) next.delete(path)
  else next.add(path)
  expandedDirs.value = next
}

function formatTime(iso: string): string {
  return iso.replace('T', ' ').substring(0, 19)
}

function statusClass(status: string): string {
  if (status === '已发版') return 'ok'
  if (status === '已注册') return 'progress'
  return 'editing'
}

function shortStatus(status: string): string {
  if (status === '已发版') return '发'
  if (status === '已注册') return '注'
  return '编'
}

/**
 * 获取文件扩展名，作为图标与徽标的智能映射依据。
 */
function fileExt(name: string): string {
  const idx = name.lastIndexOf('.')
  if (idx <= 0 || idx === name.length - 1) return 'FILE'
  return name.slice(idx + 1).toUpperCase()
}

function extClass(name: string): string {
  const ext = fileExt(name)
  if (ext === 'PY') return 'py'
  if (ext === 'JSON') return 'json'
  if (ext === 'MD') return 'md'
  if (ext === 'YAML' || ext === 'YML') return 'yaml'
  if (ext === 'SQL') return 'sql'
  return 'other'
}

function iconClassByName(name: string): string {
  const ext = fileExt(name)
  if (ext === 'PY') return 'py'
  if (ext === 'JSON') return 'json'
  if (ext === 'MD') return 'md'
  if (ext === 'YAML' || ext === 'YML') return 'yaml'
  if (ext === 'SQL') return 'sql'
  return 'other'
}

function iconClass(node: FlatNode): string {
  if (node.isDir) return 'dir'
  return iconClassByName(node.name)
}

/**
 * 拉取清单并默认展开一级目录。
 */
async function loadRows(): Promise<void> {
  const res = await axios.get('/api/v1/dev/instructions', {
    params: { keyword: keyword.value || undefined },
  })
  rows.value = res.data.data || []

  const topDirs = new Set<string>()
  for (const item of rows.value) {
    const rootDir = item.relative_path.split('/')[0]
    if (rootDir) topDirs.add(rootDir)
  }
  expandedDirs.value = topDirs
}

async function onNodeClick(node: FlatNode): Promise<void> {
  if (node.isDir) {
    toggleDir(node.path)
    return
  }
  if (!node.item) return
  selectedPath.value = node.path
  await openFile(node.item)
}

/**
 * 打开文件到标签页：已打开则激活，未打开则新建标签并拉取代码。
 */
async function openFile(item: InstructionRow): Promise<void> {
  const exists = openTabs.value.find((tab) => tab.relativePath === item.relative_path)
  if (exists) {
    activeTabPath.value = exists.relativePath
    return
  }

  const newTab: OpenTab = {
    name: item.name,
    relativePath: item.relative_path,
    item,
    code: '',
    loading: true,
    error: '',
  }
  openTabs.value.push(newTab)
  activeTabPath.value = newTab.relativePath

  try {
    const res = await axios.get('/api/v1/dev/instructions/content', {
      params: { relative_path: item.relative_path },
    })
    newTab.code = res.data.data?.content || ''
  } catch (error) {
    newTab.error = '代码加载失败，请稍后重试'
    message.error('代码加载失败')
  } finally {
    newTab.loading = false
  }
}

function activateTab(path: string): void {
  activeTabPath.value = path
  selectedPath.value = path
}

function closeTab(path: string): void {
  const idx = openTabs.value.findIndex((tab) => tab.relativePath === path)
  if (idx < 0) return
  openTabs.value.splice(idx, 1)
  if (activeTabPath.value !== path) return

  const next = openTabs.value[idx] || openTabs.value[idx - 1] || null
  activeTabPath.value = next?.relativePath || ''
  selectedPath.value = activeTabPath.value
}

function openInWorkbench(): void {
  if (!activeTab.value) return
  router.push({
    path: '/adapter-workbench',
    query: { relative_path: activeTab.value.relativePath },
  })
}

async function copyCode(): Promise<void> {
  if (!activeTab.value) return
  await navigator.clipboard.writeText(activeTab.value.code || '')
  message.success('代码已复制')
}

loadRows()
</script>

<style scoped>
.instructions-page {
  --explorer-bg: #171a1f;
  --explorer-border: #2c3442;
  --explorer-text: #c6d0dc;
  --explorer-muted: #8592a3;
  --explorer-hover: #273246;
  --explorer-active: #2c486d;
  --editor-bg: #1a1f29;
  --editor-head: #232a36;
  --editor-border: #313b4d;
  --editor-text: #d6deea;
  --editor-muted: #92a0b3;
  --brand: #4da3ff;
  position: relative;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  gap: 12px;
}

.title-wrap {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.title-wrap h2 {
  margin: 0;
  font-size: 22px;
  color: var(--text-primary);
}

.count {
  font-size: 12px;
  color: var(--text-tertiary);
}

.search-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-select {
  width: 132px;
}

.search-input {
  width: 300px;
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  padding: 8px 12px;
  background: var(--bg-card);
  color: var(--text-primary);
}

.main-grid {
  display: grid;
  grid-template-columns: minmax(330px, 35%) 1fr;
  gap: 12px;
}

.explorer {
  border: 1px solid var(--explorer-border);
  border-radius: 12px;
  background: linear-gradient(180deg, #1e232c 0%, var(--explorer-bg) 38%);
  min-height: calc(100vh - 230px);
  overflow: hidden;
}

.explorer-head {
  font-size: 12px;
  letter-spacing: 0.08em;
  font-weight: 700;
  color: #9aabc2;
  padding: 11px 12px;
  border-bottom: 1px solid #2a3140;
}

.tree-list {
  max-height: calc(100vh - 280px);
  overflow: auto;
  padding: 6px 0;
}

.tree-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 30px;
  color: var(--explorer-text);
  cursor: pointer;
  padding-right: 10px;
  border-left: 2px solid transparent;
}

.tree-row:hover {
  background: var(--explorer-hover);
}

.tree-row.active {
  background: var(--explorer-active);
  border-left-color: var(--brand);
}

.caret {
  width: 12px;
  color: var(--explorer-muted);
  text-align: center;
  flex-shrink: 0;
}

.file-icon {
  width: 15px;
  height: 14px;
  border: 1px solid #4a5a74;
  border-radius: 2px;
  position: relative;
  flex-shrink: 0;
  background: linear-gradient(180deg, #243046 0%, #1f2838 100%);
}

.file-icon.dir {
  width: 16px;
  height: 12px;
  border-radius: 2px;
  border-color: #7d6a3b;
  background: linear-gradient(180deg, #564623 0%, #4a3d22 100%);
}

.file-icon.dir::before {
  content: '';
  position: absolute;
  width: 7px;
  height: 3px;
  left: 1px;
  top: -4px;
  border: 1px solid #7d6a3b;
  border-bottom: none;
  border-radius: 2px 2px 0 0;
  background: #5c4b26;
}

.file-icon.py {
  border-color: #5c95cd;
  background: linear-gradient(135deg, #3776ab 0 52%, #ffd343 52% 100%);
}

.file-icon.json {
  border-color: #57b9ff;
  background: linear-gradient(180deg, #27354a 0%, #1f2c3e 100%);
}

.file-icon.md {
  border-color: #9c83f5;
  background: linear-gradient(180deg, #312a52 0%, #272041 100%);
}

.file-icon.yaml {
  border-color: #5dc09b;
  background: linear-gradient(180deg, #213e39 0%, #1d342f 100%);
}

.file-icon.sql {
  border-color: #d39f5b;
  background: linear-gradient(180deg, #403022 0%, #35281e 100%);
}

.file-icon.other {
  border-color: #7287a5;
  background: linear-gradient(180deg, #2a3344 0%, #222b3b 100%);
}

.file-icon .file-corner {
  position: absolute;
  right: -1px;
  top: -1px;
  width: 5px;
  height: 5px;
  background: #1a1f29;
  clip-path: polygon(100% 0, 0 0, 100% 100%);
  border-top: 1px solid #5f6d83;
  border-right: 1px solid #5f6d83;
}

.file-icon .py-mark {
  position: absolute;
  left: 3px;
  top: 3px;
  width: 8px;
  height: 8px;
}

.file-icon .py-mark::before,
.file-icon .py-mark::after {
  content: '';
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 2px;
  box-shadow: 0 0 0 1px rgba(12, 18, 29, 0.2);
}

.file-icon .py-mark::before {
  left: 0;
  top: 0;
  background: #2f6fa6;
}

.file-icon .py-mark::after {
  right: 0;
  bottom: 0;
  background: #efc438;
}

.tree-row:hover .file-icon {
  filter: brightness(1.08);
}

.tree-row.active .file-icon {
  box-shadow: 0 0 0 1px rgba(135, 198, 255, 0.35);
}

.tree-name {
  font-size: 13px;
  max-width: 220px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ext-badge {
  margin-left: auto;
  margin-right: 6px;
  min-width: 30px;
  height: 16px;
  padding: 0 6px;
  border-radius: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.02em;
  border: 1px solid transparent;
}

.ext-badge.py {
  background: rgba(78, 192, 142, 0.16);
  color: #75ddaa;
  border-color: rgba(78, 192, 142, 0.35);
}

.ext-badge.json {
  background: rgba(99, 165, 255, 0.16);
  color: #8dc3ff;
  border-color: rgba(99, 165, 255, 0.38);
}

.ext-badge.md {
  background: rgba(175, 146, 245, 0.16);
  color: #c7b4ff;
  border-color: rgba(175, 146, 245, 0.36);
}

.ext-badge.yaml {
  background: rgba(98, 196, 159, 0.16);
  color: #8fe2c1;
  border-color: rgba(98, 196, 159, 0.36);
}

.ext-badge.sql {
  background: rgba(211, 159, 91, 0.16);
  color: #efc98f;
  border-color: rgba(211, 159, 91, 0.38);
}

.ext-badge.other {
  background: rgba(173, 149, 111, 0.16);
  color: #e2c48f;
  border-color: rgba(173, 149, 111, 0.34);
}

.status-pill-mini {
  min-width: 18px;
  height: 18px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid transparent;
}

.editor {
  border: 1px solid var(--editor-border);
  border-radius: 12px;
  background: var(--editor-bg);
  min-height: calc(100vh - 230px);
  overflow: hidden;
}

.editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  background: var(--editor-head);
  border-bottom: 1px solid var(--editor-border);
}

.tabs-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  flex: 1;
  padding-bottom: 2px;
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 260px;
  background: #1f2632;
  border: 1px solid #2d3748;
  color: #b7c5d8;
  font-size: 12.5px;
  padding: 5px 6px 5px 10px;
  border-radius: 7px;
  cursor: pointer;
}

.tab.active {
  color: #deebfb;
  border-color: #5075a5;
  background: #2a3446;
}

.tab-icon {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background: #7488a6;
  flex-shrink: 0;
}

.tab-icon.py {
  background: linear-gradient(135deg, #3776ab 0 52%, #ffd343 52% 100%);
}

.tab-icon.json {
  background: #5bb9ff;
}

.tab-icon.md {
  background: #a58df6;
}

.tab-icon.yaml {
  background: #64cca6;
}

.tab-icon.sql {
  background: #d6a35e;
}

.tab-title {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.tab-close {
  width: 17px;
  height: 17px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #8fa2bb;
  flex-shrink: 0;
}

.tab-close:hover {
  background: #3a4961;
  color: #dce8f8;
}

.tab-empty {
  color: var(--editor-muted);
  font-size: 12px;
  padding-left: 2px;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ghost-btn {
  border: 1px solid #3b465a;
  background: #2a3344;
  color: #d2deed;
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
}

.ghost-btn:hover {
  background: #33435d;
  border-color: #5e7fa9;
}

.ghost-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.meta-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  padding: 10px 12px;
  border-bottom: 1px dashed #354154;
  color: var(--editor-muted);
  font-size: 12px;
}

.meta-bar b {
  font-weight: 700;
}

.mono {
  font-family: var(--font-mono);
}

.code-panel {
  min-height: calc(100vh - 355px);
  max-height: calc(100vh - 355px);
  overflow: auto;
  background: #11151d;
}

.code-lines {
  font-family: var(--font-mono);
  font-size: 12.5px;
  line-height: 1.6;
  color: #d7e2f2;
}

.code-line {
  display: grid;
  grid-template-columns: 56px 1fr;
}

.line-no {
  color: #6d7f96;
  text-align: right;
  padding: 0 12px 0 8px;
  user-select: none;
  border-right: 1px solid #263041;
  background: #121824;
}

.line-text {
  white-space: pre;
  padding: 0 12px;
}

.code-placeholder {
  margin: 0;
  padding: 14px;
  min-height: calc(100vh - 355px);
  color: #8fa2b9;
  font-family: var(--font-mono);
  font-size: 12.5px;
}

.empty-cell {
  text-align: center;
  color: var(--explorer-muted);
  padding: 24px;
}

.ok {
  color: #55cb8e;
  background: rgba(73, 185, 125, 0.16);
  border-color: rgba(85, 203, 142, 0.42);
}

.progress {
  color: #7dc0ff;
  background: rgba(76, 147, 223, 0.18);
  border-color: rgba(125, 192, 255, 0.44);
}

.editing {
  color: #c7b08c;
  background: rgba(179, 139, 84, 0.18);
  border-color: rgba(199, 176, 140, 0.4);
}

@media (max-width: 1180px) {
  .editor-head {
    flex-direction: column;
    align-items: stretch;
  }

  .head-actions {
    justify-content: flex-end;
  }
}

@media (max-width: 1080px) {
  .main-grid {
    grid-template-columns: 1fr;
  }

  .code-panel,
  .code-placeholder {
    min-height: 360px;
    max-height: 360px;
  }
}
</style>
