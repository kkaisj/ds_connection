<!--
  存储管理页面
  卡片式展示存储配置，支持新增/编辑/删除。
  按存储类型动态渲染配置表单（参考 img/ 下的参考图）：
  - MySQL：地址、用户名、密码、库名、端口、SQL转义开关、SSL、最大连接数
  - 飞书多维表（授权码）：授权码、app_token、table_id
  - 钉钉AI表格：clientId、clientSecret、baseId、sheetId、sheetName、userId
  - 邮箱：SMTP服务器、端口、发件人、授权码、收件人
-->
<template>
  <div class="storages-page">
    <div class="page-header">
      <h2 class="section-title">存储配置</h2>
      <span class="section-desc">管理数据落地的目标存储，支持多种存储类型</span>
    </div>

    <div class="card-grid">
      <div v-for="(s, i) in storages" :key="s.id" class="storage-card" :style="{ animationDelay: `${0.05 * i}s` }">
        <div class="card-body">
          <div class="card-header">
            <div class="type-icon" :class="`icon-${getTypeColor(s.type)}`">{{ typeIcon(s.type) }}</div>
            <span class="status-badge" :class="`status-${s.status}`">{{ s.status === 'active' ? '启用' : '停用' }}</span>
          </div>
          <h3 class="storage-name">{{ s.name }}</h3>
          <div class="type-label">{{ typeLabel(s.type) }}</div>
          <div class="card-footer">
            <span class="create-time">{{ formatDate(s.created_at) }}</span>
            <div class="footer-actions">
              <button class="edit-btn" @click="openEdit(s)">编辑</button>
              <button class="delete-btn" @click="confirmDelete(s.id, s.name)">删除</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 新增卡片 -->
      <div class="storage-card add-card" @click="openCreate">
        <div class="add-body">
          <span class="add-icon">+</span>
          <span class="add-text">添加存储配置</span>
        </div>
      </div>
    </div>

    <!-- ════════ 新增弹窗 ════════ -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">{{ isEdit ? '编辑存储' : '新增存储' }}</h3>
          <button class="modal-close" @click="showModal = false">&times;</button>
        </div>

        <div class="modal-body">
          <!-- 存储名称（必填） -->
          <div class="form-group">
            <label class="form-label required">存储名称</label>
            <input v-model="form.name" class="form-input" placeholder="请输入" />
          </div>

          <!-- 存储平台选择 -->
          <div class="form-group">
            <label class="form-label">存储平台</label>
            <DcSelect v-model="form.type" :options="storageTypeOptions" />
          </div>

          <!-- ──── MySQL 配置 ──── -->
          <template v-if="form.type === 'mysql'">
            <div class="form-group">
              <label class="form-label required">数据库地址(域名或IP)</label>
              <input v-model="form.host" class="form-input" placeholder="请输入" />
            </div>
            <div class="form-group">
              <label class="form-label required">用户名</label>
              <input v-model="form.username" class="form-input" placeholder="请输入" />
            </div>
            <div class="form-group">
              <label class="form-label required">密码</label>
              <div class="input-with-icon">
                <input v-model="form.password" :type="showPwd ? 'text' : 'password'" class="form-input" placeholder="请输入" />
                <button class="icon-btn" @click="showPwd = !showPwd">
                  {{ showPwd ? '🙈' : '👁' }}
                </button>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label required">数据库名</label>
              <input v-model="form.database" class="form-input" placeholder="请输入" />
            </div>
            <div class="form-group">
              <label class="form-label">端口</label>
              <input v-model="form.port" class="form-input" placeholder="3306" />
            </div>
            <div class="form-group">
              <label class="form-label required">启用SQL转义(useEscape)</label>
              <div class="toggle-row">
                <button class="toggle-btn" :class="form.use_escape ? 'toggle-on' : 'toggle-off'" @click="form.use_escape = !form.use_escape">
                  <span class="toggle-knob"></span>
                </button>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">是否使用SSL协议</label>
              <DcSelect v-model="form.use_ssl" :options="boolOptions" />
            </div>
            <div class="form-group">
              <label class="form-label">最大连接数</label>
              <input v-model="form.max_connections" class="form-input" type="number" placeholder="16" />
            </div>
          </template>

          <!-- ──── 飞书多维表(授权码) ──── -->
          <template v-if="form.type === 'feishu_bitable'">
            <div class="form-group">
              <label class="form-label">多维表格授权码 <a class="doc-link" href="javascript:void(0)">查看对接文档</a></label>
              <input v-model="form.feishu_auth_code" class="form-input" placeholder="请输入" />
            </div>
            <div class="form-group">
              <label class="form-label">app_token</label>
              <input v-model="form.feishu_app_token" class="form-input" placeholder="请输入" />
            </div>
            <div class="form-group">
              <label class="form-label">table_id</label>
              <input v-model="form.feishu_table_id" class="form-input" placeholder="请输入" />
            </div>
          </template>

          <!-- ──── 钉钉AI表格 ──── -->
          <template v-if="form.type === 'dingtalk_sheet'">
            <div class="form-group">
              <label class="form-label required">clientId <a class="doc-link" href="javascript:void(0)">查看对接文档</a></label>
              <input v-model="form.dingtalk_client_id" class="form-input" placeholder="请输入" />
            </div>
            <div class="form-group">
              <label class="form-label required">clientSecret</label>
              <input v-model="form.dingtalk_client_secret" class="form-input" placeholder="请输入" />
            </div>
            <div class="form-group">
              <label class="form-label required">baseId</label>
              <input v-model="form.dingtalk_base_id" class="form-input" placeholder="请输入" />
            </div>
            <div class="form-group">
              <label class="form-label required">sheetId</label>
              <input v-model="form.dingtalk_sheet_id" class="form-input" placeholder="请输入" />
            </div>
            <div class="form-group">
              <label class="form-label required">sheetName</label>
              <input v-model="form.dingtalk_sheet_name" class="form-input" placeholder="请输入" />
            </div>
            <div class="form-group">
              <label class="form-label required">userId</label>
              <input v-model="form.dingtalk_user_id" class="form-input" placeholder="请输入" />
            </div>
          </template>

          <!-- ──── 邮箱存储 ──── -->
          <template v-if="form.type === 'email'">
            <div class="form-group">
              <label class="form-label required">SMTP 服务器</label>
              <input v-model="form.email_smtp_host" class="form-input" placeholder="smtp.qq.com" />
            </div>
            <div class="form-group">
              <label class="form-label">SMTP 端口</label>
              <input v-model="form.email_smtp_port" class="form-input" placeholder="465" />
            </div>
            <div class="form-group">
              <label class="form-label required">发件人邮箱</label>
              <input v-model="form.email_sender" class="form-input" placeholder="example@qq.com" />
            </div>
            <div class="form-group">
              <label class="form-label required">邮箱授权码</label>
              <div class="input-with-icon">
                <input v-model="form.email_auth_code" :type="showPwd ? 'text' : 'password'" class="form-input" placeholder="邮箱 SMTP 授权码" />
                <button class="icon-btn" @click="showPwd = !showPwd">
                  {{ showPwd ? '🙈' : '👁' }}
                </button>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label required">收件人邮箱</label>
              <input v-model="form.email_receiver" class="form-input" placeholder="接收数据的邮箱地址" />
            </div>
          </template>
        </div>

        <div class="modal-footer">
          <button class="modal-btn cancel" @click="showModal = false">取消</button>
          <button class="modal-btn confirm" @click="submitForm">保存</button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <DcConfirm
      v-model:show="showDeleteConfirm"
      title="确认删除？"
      :desc="`确定要删除存储配置「${deleteName}」吗？删除后不可恢复。`"
      confirm-text="删除"
      :danger="true"
      @confirm="doDelete"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 存储管理页面逻辑
 * - 卡片列表展示已配置的存储
 * - 新增弹窗按存储类型动态渲染不同的配置表单
 * - 提交时将表单字段组装为 config JSON 提交给后端
 */
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'
import DcSelect from '@/components/DcSelect.vue'
import DcConfirm from '@/components/DcConfirm.vue'

const message = useMessage()

/* ── 类型 ── */
interface StorageItem { id: number; type: string; name: string; status: string; created_at: string | null }

/* ── 状态 ── */
const storages = ref<StorageItem[]>([])
const showModal = ref(false)
const showPwd = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)

/* ── 删除确认 ── */
const showDeleteConfirm = ref(false)
const deleteTargetId = ref<number | null>(null)
const deleteName = ref('')

/* ── 下拉选项 ── */
const storageTypeOptions = [
  { value: 'mysql', label: 'MySQL数据库' },
  { value: 'feishu_bitable', label: '飞书多维表格(授权码)' },
  { value: 'dingtalk_sheet', label: '钉钉AI表格' },
  { value: 'email', label: '邮箱' },
]

const boolOptions = [
  { value: 'false', label: 'false' },
  { value: 'true', label: 'true' },
]

/* ── 表单（所有类型字段扁平化，提交时按类型组装） ── */
const defaultForm = () => ({
  type: 'mysql',
  name: '',
  // MySQL
  host: '', username: '', password: '', database: '', port: '3306',
  use_escape: true, use_ssl: 'false', max_connections: '16',
  // 飞书
  feishu_auth_code: '', feishu_app_token: '', feishu_table_id: '',
  // 钉钉
  dingtalk_client_id: '', dingtalk_client_secret: '', dingtalk_base_id: '',
  dingtalk_sheet_id: '', dingtalk_sheet_name: '', dingtalk_user_id: '',
  // 邮箱
  email_smtp_host: '', email_smtp_port: '465', email_sender: '',
  email_auth_code: '', email_receiver: '',
})

const form = ref(defaultForm())

/* ── 工具函数 ── */
const typeLabels: Record<string, string> = {
  mysql: 'MySQL 数据库', feishu_bitable: '飞书多维表格', dingtalk_sheet: '钉钉AI表格', email: '邮箱存储',
}
function typeLabel(t: string) { return typeLabels[t] || t }
function typeIcon(t: string) {
  if (t === 'mysql') return 'DB'
  if (t === 'feishu_bitable') return '飞'
  if (t === 'dingtalk_sheet') return '钉'
  if (t === 'email') return '邮'
  return '?'
}
function getTypeColor(t: string) {
  if (t === 'mysql') return 'blue'
  if (t === 'feishu_bitable') return 'copper'
  if (t === 'dingtalk_sheet') return 'green'
  if (t === 'email') return 'amber'
  return 'copper'
}
function formatDate(iso: string | null) { return iso ? iso.split('T')[0] : '--' }

/* ── 数据加载 ── */
async function loadStorages() {
  const res = await axios.get('/api/v1/storages')
  storages.value = res.data.data
}

/* ── 打开新增弹窗 ── */
function openCreate() {
  isEdit.value = false
  editId.value = null
  form.value = defaultForm()
  showPwd.value = false
  showModal.value = true
}

/* ── 打开编辑弹窗（回填已有数据） ── */
function openEdit(s: StorageItem) {
  isEdit.value = true
  editId.value = s.id
  showPwd.value = false
  // 先重置再填充基本信息，config 需要从后端获取（当前列表接口没返回 config）
  form.value = { ...defaultForm(), type: s.type, name: s.name }
  showModal.value = true
}

/* ── 确认删除 ── */
function confirmDelete(id: number, name: string) {
  deleteTargetId.value = id
  deleteName.value = name
  showDeleteConfirm.value = true
}

async function doDelete() {
  if (!deleteTargetId.value) return
  await axios.delete(`/api/v1/storages/${deleteTargetId.value}`)
  message.success('存储配置已删除')
  deleteTargetId.value = null
  await loadStorages()
}

/* ── 按存储类型组装 config JSON ── */
function buildConfig(): Record<string, string | boolean> {
  const f = form.value
  if (f.type === 'mysql') {
    return {
      host: f.host, username: f.username, password: f.password,
      database: f.database, port: f.port,
      use_escape: f.use_escape, use_ssl: f.use_ssl, max_connections: f.max_connections,
    }
  }
  if (f.type === 'feishu_bitable') {
    return {
      auth_code: f.feishu_auth_code, app_token: f.feishu_app_token, table_id: f.feishu_table_id,
    }
  }
  if (f.type === 'dingtalk_sheet') {
    return {
      client_id: f.dingtalk_client_id, client_secret: f.dingtalk_client_secret,
      base_id: f.dingtalk_base_id, sheet_id: f.dingtalk_sheet_id,
      sheet_name: f.dingtalk_sheet_name, user_id: f.dingtalk_user_id,
    }
  }
  if (f.type === 'email') {
    return {
      smtp_host: f.email_smtp_host, smtp_port: f.email_smtp_port,
      sender: f.email_sender, auth_code: f.email_auth_code, receiver: f.email_receiver,
    }
  }
  return {}
}

/* ── 提交（新增或编辑） ── */
async function submitForm() {
  if (!form.value.name) { message.warning('请输入存储名称'); return }

  const config = buildConfig()

  if (isEdit.value && editId.value) {
    await axios.patch(`/api/v1/storages/${editId.value}`, { name: form.value.name, config })
    message.success('存储配置已更新')
  } else {
    await axios.post('/api/v1/storages', { type: form.value.type, name: form.value.name, config })
    message.success('存储配置已创建')
  }
  showModal.value = false
  await loadStorages()
}

onMounted(loadStorages)
</script>

<style scoped>
/* ── 页面标题 ── */
.page-header { margin-bottom: 22px; }
.section-title {
  font-family: var(--font-display); font-size: 18px; font-weight: 600;
  color: var(--text-primary); margin-bottom: 4px;
}
.section-desc { font-size: 13px; color: var(--text-tertiary); }

/* ── 卡片网格 ── */
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 18px; }
.storage-card {
  background: var(--bg-card); border-radius: var(--radius-md); border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  opacity: 0; transform: translateY(16px); animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.storage-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.card-body { padding: 22px; }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.type-icon {
  width: 40px; height: 40px; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; font-family: var(--font-mono);
}
.icon-blue { background: var(--accent-blue-bg); color: var(--accent-blue); }
.icon-copper { background: var(--accent-copper-bg); color: var(--accent-copper); }
.icon-green { background: var(--accent-green-bg); color: var(--accent-green); }
.icon-amber { background: var(--accent-amber-bg); color: var(--accent-amber); }
.status-badge { padding: 3px 10px; border-radius: var(--radius-pill); font-size: 11px; font-weight: 550; }
.status-active { background: var(--accent-green-bg); color: var(--accent-green); }
.status-inactive { background: var(--accent-amber-bg); color: var(--accent-amber); }
.storage-name { font-family: var(--font-display); font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.type-label { font-size: 12.5px; color: var(--text-tertiary); margin-bottom: 18px; }
.card-footer { display: flex; align-items: center; justify-content: space-between; }
.create-time { font-size: 11.5px; color: var(--text-tertiary); }
.footer-actions { display: flex; gap: 6px; }
.edit-btn, .delete-btn {
  padding: 4px 14px; border-radius: 6px; font-size: 12px; font-weight: 500;
  border: 1px solid var(--border); background: var(--bg-card); cursor: pointer; transition: all 0.2s; font-family: var(--font-body);
}
.edit-btn { color: var(--text-secondary); }
.edit-btn:hover { border-color: var(--accent-copper-light); color: var(--accent-copper); }
.delete-btn { color: var(--accent-red); border-color: var(--accent-red-light); }
.delete-btn:hover { background: var(--accent-red); color: white; border-color: var(--accent-red); }

/* 新增卡片 */
.add-card { border: 2px dashed var(--border); cursor: pointer; opacity: 1 !important; transform: none !important; animation: none !important; }
.add-card:hover { border-color: var(--accent-copper-light); }
.add-body { padding: 22px; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 160px; gap: 8px; }
.add-icon { font-size: 28px; color: var(--text-tertiary); font-weight: 300; }
.add-text { font-size: 13px; color: var(--text-tertiary); }

/* ════════ 弹窗 ════════ */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(45,42,38,0.3); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-card {
  background: var(--bg-card); border-radius: var(--radius-lg);
  width: 480px; max-width: 92vw; max-height: 85vh;
  box-shadow: var(--shadow-lg); animation: fadeUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex; flex-direction: column;
}

/* 弹窗头部 */
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 22px 28px 0;
}
.modal-title {
  font-family: var(--font-display); font-size: 18px; font-weight: 600; color: var(--text-primary);
}
.modal-close {
  background: none; border: none; font-size: 22px; color: var(--text-tertiary);
  cursor: pointer; padding: 4px 8px; border-radius: 4px; transition: all 0.15s; line-height: 1;
}
.modal-close:hover { background: var(--bg-subtle); color: var(--text-primary); }

/* 弹窗内容（可滚动） */
.modal-body {
  padding: 20px 28px; overflow-y: auto; flex: 1;
}

/* 表单 */
.form-group { margin-bottom: 18px; }
.form-label {
  display: block; font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px;
}
.form-label.required::before { content: '* '; color: var(--accent-red); }
.form-input {
  width: 100%; padding: 9px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--bg-base); font-size: 13px; font-family: var(--font-body); color: var(--text-primary); outline: none;
  transition: border-color 0.2s;
}
.form-input:focus { border-color: var(--accent-copper); }
.form-input::placeholder { color: var(--text-tertiary); }

/* 密码框带眼睛图标 */
.input-with-icon { position: relative; }
.input-with-icon .form-input { padding-right: 40px; }
.icon-btn {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  background: none; border: none; cursor: pointer; font-size: 16px; padding: 4px;
  color: var(--text-tertiary); transition: color 0.15s;
}
.icon-btn:hover { color: var(--text-secondary); }

/* Toggle 开关 */
.toggle-row { display: flex; align-items: center; gap: 10px; }
.toggle-btn {
  width: 40px; height: 22px; border-radius: 11px; border: none;
  cursor: pointer; position: relative; transition: background 0.2s; padding: 0;
}
.toggle-off { background: var(--border); }
.toggle-on { background: var(--accent-copper); }
.toggle-knob {
  position: absolute; top: 2px; width: 18px; height: 18px;
  border-radius: 50%; background: white; transition: left 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.toggle-off .toggle-knob { left: 2px; }
.toggle-on .toggle-knob { left: 20px; }

/* 文档链接 */
.doc-link {
  font-size: 12px; color: var(--accent-blue); text-decoration: none; margin-left: 8px; font-weight: 400;
}
.doc-link:hover { text-decoration: underline; }

/* 底部按钮 */
.modal-footer {
  display: flex; justify-content: flex-end; gap: 10px;
  padding: 16px 28px; border-top: 1px solid var(--border-light);
}
.modal-btn {
  padding: 8px 24px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500;
  cursor: pointer; font-family: var(--font-body); transition: all 0.2s;
}
.modal-btn.cancel { background: var(--bg-subtle); border: 1px solid var(--border); color: var(--text-secondary); }
.modal-btn.cancel:hover { border-color: var(--text-tertiary); }
.modal-btn.confirm { background: var(--accent-red); border: none; color: white; }
.modal-btn.confirm:hover { opacity: 0.9; }
</style>
