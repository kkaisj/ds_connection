<!--
  账号管理页面
  展示店铺账号列表，支持新增/编辑/删除。
  敏感信息脱敏展示，健康分可视化，验证码转发可选配置。
-->
<template>
  <div class="accounts-page">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-group">
        <DcSelect
          v-model="filterPlatform"
          :options="platformOptions"
          placeholder="全部平台"
          @change="loadAccounts"
        />
        <DcSelect
          v-model="filterStatus"
          :options="accountStatusOptions"
          placeholder="全部状态"
          @change="loadAccounts"
        />
      </div>
      <button class="add-btn" @click="openCreate">+ 新增账号</button>
    </div>

    <!-- 账号卡片 -->
    <div class="account-grid">
      <div v-for="(acc, i) in accounts" :key="acc.id" class="account-card" :style="{ animationDelay: `${0.05 * i}s` }">
        <div class="card-top-bar" :class="`bar-${getStatusColor(acc.status)}`"></div>
        <div class="card-body">
          <div class="card-header">
            <span class="platform-tag">{{ acc.platform_name }}</span>
            <span class="status-badge" :class="`status-${acc.status}`">
              <span class="status-dot"></span>{{ statusLabel(acc.status) }}
            </span>
          </div>
          <h3 class="shop-name">{{ acc.shop_name }}</h3>
          <div class="info-row">
            <span class="info-label">账号</span>
            <span class="info-value">{{ acc.username_masked }}</span>
          </div>

          <!-- 验证码转发标签：仅在非 none 时展示 -->
          <div v-if="acc.captcha_method !== 'none'" class="captcha-badge-row">
            <span class="captcha-badge" :class="acc.captcha_enabled ? 'captcha-on' : 'captcha-off'">
              <span class="captcha-dot"></span>
              {{ captchaMethodLabel(acc.captcha_method) }}
              {{ acc.captcha_enabled ? '' : '(已关闭)' }}
            </span>
          </div>

          <!-- 健康分 -->
          <div class="health-section">
            <div class="health-header">
              <span class="info-label">健康分</span>
              <span class="health-score" :class="getScoreClass(acc.health_score)">{{ acc.health_score }}</span>
            </div>
            <div class="health-bar-wrap">
              <div class="health-bar" :style="{ width: `${acc.health_score}%`, background: getScoreColor(acc.health_score) }"></div>
            </div>
          </div>

          <div class="card-footer">
            <span class="create-time">{{ formatDate(acc.created_at) }}</span>
            <div class="footer-actions">
              <button class="edit-btn" @click="openEdit(acc)">编辑</button>
              <button class="delete-btn" @click="confirmDelete(acc.id, acc.shop_name)">删除</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ════════ 新增/编辑弹窗 ════════ -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-card">
        <h3 class="modal-title">{{ isEdit ? '编辑账号' : '新增账号' }}</h3>

        <!-- 基本信息 -->
        <div class="form-group">
          <label class="form-label">平台</label>
          <DcSelect v-model="form.platform_id" :options="platformIdOptions" :disabled="isEdit" />
        </div>
        <div class="form-group">
          <label class="form-label">店铺名称</label>
          <input v-model="form.shop_name" class="form-input" placeholder="请输入店铺名称" />
        </div>
        <div v-if="!isEdit" class="form-group">
          <label class="form-label">用户名</label>
          <input v-model="form.username" class="form-input" placeholder="平台登录用户名" />
        </div>
        <div class="form-group">
          <label class="form-label">{{ isEdit ? '新密码（留空不修改）' : '密码' }}</label>
          <input v-model="form.password" type="password" class="form-input" placeholder="平台登录密码" />
        </div>
        <div v-if="isEdit" class="form-group">
          <label class="form-label">状态</label>
          <DcSelect v-model="form.status" :options="accountStatusOptions" />
        </div>

        <!-- 验证码转发配置（折叠区） -->
        <div class="captcha-section">
          <div class="section-header" @click="captchaExpanded = !captchaExpanded">
            <span class="section-title">验证码转发配置</span>
            <span class="section-toggle">{{ captchaExpanded ? '收起' : '展开' }}</span>
          </div>

          <div v-if="captchaExpanded" class="section-body">
            <div class="form-group">
              <label class="form-label">转发方式</label>
              <DcSelect v-model="form.captcha_method" :options="captchaMethodOptions" />
            </div>

            <!-- 开关：仅在选择了方式时显示 -->
            <div v-if="form.captcha_method !== 'none'" class="form-group">
              <label class="form-label">启用转发</label>
              <div class="toggle-row">
                <button
                  class="toggle-btn"
                  :class="form.captcha_enabled ? 'toggle-on' : 'toggle-off'"
                  @click="form.captcha_enabled = !form.captcha_enabled"
                >
                  <span class="toggle-knob"></span>
                </button>
                <span class="toggle-label">{{ form.captcha_enabled ? '已启用' : '已关闭' }}</span>
              </div>
            </div>

            <!-- 短信转发配置 -->
            <template v-if="form.captcha_method === 'sms_forward'">
              <div class="form-group">
                <label class="form-label">接收手机号</label>
                <input v-model="form.captcha_phone" class="form-input" placeholder="接收验证码的手机号" />
              </div>
              <div class="form-group">
                <label class="form-label">转发 Webhook</label>
                <input v-model="form.captcha_webhook" class="form-input" placeholder="短信转发服务的回调地址" />
              </div>
            </template>

            <!-- 邮件转发配置 -->
            <template v-if="form.captcha_method === 'email_forward'">
              <div class="form-group">
                <label class="form-label">接收邮箱</label>
                <input v-model="form.captcha_email" class="form-input" placeholder="example@qq.com" />
              </div>
              <div class="form-row">
                <div class="form-group flex1">
                  <label class="form-label">IMAP 服务器</label>
                  <input v-model="form.captcha_imap_host" class="form-input" placeholder="imap.qq.com" />
                </div>
                <div class="form-group" style="width: 100px;">
                  <label class="form-label">端口</label>
                  <input v-model="form.captcha_imap_port" class="form-input" placeholder="993" />
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">邮箱授权码</label>
                <input v-model="form.captcha_email_auth" type="password" class="form-input" placeholder="IMAP 登录授权码" />
              </div>
            </template>

            <!-- 邮箱授权码配置 -->
            <template v-if="form.captcha_method === 'email_auth_code'">
              <div class="form-group">
                <label class="form-label">邮箱地址</label>
                <input v-model="form.captcha_email" class="form-input" placeholder="example@qq.com" />
              </div>
              <div class="form-group">
                <label class="form-label">授权码</label>
                <input v-model="form.captcha_email_auth" type="password" class="form-input" placeholder="邮箱独立密码/授权码" />
              </div>
            </template>

            <!-- 人工输入：无需额外配置 -->
            <p v-if="form.captcha_method === 'manual'" class="captcha-hint">
              任务执行到需要验证码时将暂停，等待人工在页面上手动输入验证码后继续。
            </p>
          </div>
        </div>

        <div class="modal-footer">
          <button class="modal-btn cancel" @click="showModal = false">取消</button>
          <button class="modal-btn confirm" @click="submitForm">{{ isEdit ? '保存' : '创建' }}</button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <DcConfirm
      v-model:show="showDeleteConfirm"
      title="确认删除账号？"
      :desc="`确定要删除店铺「${deleteAccName}」吗？删除后不可恢复。`"
      confirm-text="删除"
      :danger="true"
      @confirm="doDeleteAccount"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 账号管理页面逻辑
 * - 列表展示：卡片式，含验证码转发标签
 * - 新增/编辑弹窗：基本信息 + 可选的验证码转发折叠区
 * - 验证码配置按转发方式动态渲染不同表单字段
 */
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'
import DcSelect from '@/components/DcSelect.vue'
import DcConfirm from '@/components/DcConfirm.vue'

const message = useMessage()

/* ── 类型 ── */
interface AccountItem {
  id: number; shop_name: string; username_masked: string; status: string;
  health_score: number; platform_code: string; platform_name: string;
  captcha_method: string; captcha_config: Record<string, string> | null; captcha_enabled: boolean;
  created_at: string | null
}

/* ── 列表状态 ── */
const accounts = ref<AccountItem[]>([])
const filterPlatform = ref('')
const filterStatus = ref('')

/* ── 下拉选项 ── */
const platformOptions = [
  { value: '', label: '全部平台' },
  { value: 'taobao', label: '淘宝天猫' },
  { value: 'jd', label: '京东' },
  { value: 'pdd', label: '拼多多' },
  { value: 'douyin', label: '抖音' },
]
const accountStatusOptions = [
  { value: '', label: '全部状态' },
  { value: 'active', label: '正常' },
  { value: 'inactive', label: '停用' },
  { value: 'disabled', label: '禁用' },
]

/* ── 弹窗内选项 ── */
const platformIdOptions = [
  { value: 1, label: '淘宝天猫' },
  { value: 2, label: '京东' },
  { value: 3, label: '拼多多' },
  { value: 4, label: '抖音' },
]
const captchaMethodOptions = [
  { value: 'none', label: '不需要验证码' },
  { value: 'sms_forward', label: '手机短信转发' },
  { value: 'email_forward', label: '邮件转发 (IMAP)' },
  { value: 'email_auth_code', label: '邮箱授权码' },
  { value: 'manual', label: '人工输入' },
]

/* ── 弹窗状态 ── */
const showModal = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const captchaExpanded = ref(false)

/* ── 删除确认 ── */
const showDeleteConfirm = ref(false)
const deleteTargetId = ref<number | null>(null)
const deleteAccName = ref('')

/* ── 表单（含验证码字段的扁平化结构，提交时组装成 captcha_config） ── */
const form = ref({
  platform_id: 1,
  shop_name: '',
  username: '',
  password: '',
  status: 'active',
  captcha_method: 'none',
  captcha_enabled: false,
  // 短信转发
  captcha_phone: '',
  captcha_webhook: '',
  // 邮件转发 / 邮箱授权码
  captcha_email: '',
  captcha_imap_host: '',
  captcha_imap_port: '993',
  captcha_email_auth: '',
})

/* ── 字典 ── */
const statusMap: Record<string, string> = { active: '正常', inactive: '停用', disabled: '禁用' }
function statusLabel(s: string) { return statusMap[s] || s }

const captchaLabels: Record<string, string> = {
  none: '无', sms_forward: '短信转发', email_forward: '邮件转发',
  email_auth_code: '邮箱授权码', manual: '人工输入',
}
function captchaMethodLabel(m: string) { return captchaLabels[m] || m }

function getStatusColor(s: string) { return s === 'active' ? 'green' : s === 'inactive' ? 'amber' : 'red' }
function getScoreClass(score: number) { return score >= 70 ? 'score-good' : score >= 30 ? 'score-warn' : 'score-bad' }
function getScoreColor(score: number) { return score >= 70 ? 'var(--accent-green)' : score >= 30 ? 'var(--accent-amber)' : 'var(--accent-red)' }
function formatDate(iso: string | null) { return iso ? iso.split('T')[0] : '--' }

/* ── 数据加载 ── */
async function loadAccounts() {
  const params: Record<string, string> = {}
  if (filterPlatform.value) params.platform = filterPlatform.value
  if (filterStatus.value) params.status = filterStatus.value
  const res = await axios.get('/api/v1/accounts', { params })
  accounts.value = res.data.data
}

/* ── 打开新增弹窗 ── */
function openCreate() {
  isEdit.value = false
  editId.value = null
  captchaExpanded.value = false
  form.value = {
    platform_id: 1, shop_name: '', username: '', password: '', status: 'active',
    captcha_method: 'none', captcha_enabled: false,
    captcha_phone: '', captcha_webhook: '',
    captcha_email: '', captcha_imap_host: '', captcha_imap_port: '993', captcha_email_auth: '',
  }
  showModal.value = true
}

/* ── 打开编辑弹窗，回填验证码配置 ── */
function openEdit(acc: AccountItem) {
  isEdit.value = true
  editId.value = acc.id
  const platformIds: Record<string, number> = { taobao: 1, jd: 2, pdd: 3, douyin: 4 }
  const cfg = acc.captcha_config || {}

  form.value = {
    platform_id: platformIds[acc.platform_code] || 1,
    shop_name: acc.shop_name,
    username: '',
    password: '',
    status: acc.status,
    captcha_method: acc.captcha_method,
    captcha_enabled: acc.captcha_enabled,
    captcha_phone: cfg.phone || '',
    captcha_webhook: cfg.webhook || '',
    captcha_email: cfg.email || '',
    captcha_imap_host: cfg.imap_host || '',
    captcha_imap_port: cfg.imap_port || '993',
    captcha_email_auth: cfg.email_auth || '',
  }

  // 如果已配置了验证码，自动展开
  captchaExpanded.value = acc.captcha_method !== 'none'
  showModal.value = true
}

/* ── 组装 captcha_config JSON ── */
function buildCaptchaConfig(): Record<string, string> | null {
  const m = form.value.captcha_method
  if (m === 'none' || m === 'manual') return null
  if (m === 'sms_forward') {
    return { phone: form.value.captcha_phone, webhook: form.value.captcha_webhook }
  }
  if (m === 'email_forward') {
    return {
      email: form.value.captcha_email,
      imap_host: form.value.captcha_imap_host,
      imap_port: form.value.captcha_imap_port,
      email_auth: form.value.captcha_email_auth,
    }
  }
  if (m === 'email_auth_code') {
    return { email: form.value.captcha_email, email_auth: form.value.captcha_email_auth }
  }
  return null
}

/* ── 提交 ── */
async function submitForm() {
  if (!form.value.shop_name) { message.warning('请输入店铺名称'); return }
  if (!isEdit.value && !form.value.username) { message.warning('请输入用户名'); return }

  const captchaConfig = buildCaptchaConfig()

  if (isEdit.value) {
    const body: Record<string, unknown> = {
      shop_name: form.value.shop_name,
      status: form.value.status,
      captcha_method: form.value.captcha_method,
      captcha_config: captchaConfig,
      captcha_enabled: form.value.captcha_enabled,
    }
    if (form.value.password) body.password = form.value.password
    await axios.patch(`/api/v1/accounts/${editId.value}`, body)
    message.success('账号已更新')
  } else {
    await axios.post('/api/v1/accounts', {
      platform_id: form.value.platform_id,
      shop_name: form.value.shop_name,
      username: form.value.username,
      password: form.value.password,
      captcha_method: form.value.captcha_method,
      captcha_config: captchaConfig,
      captcha_enabled: form.value.captcha_enabled,
    })
    message.success('账号已创建')
  }
  showModal.value = false
  await loadAccounts()
}

/* ── 删除 ── */
/* ── 确认删除 ── */
function confirmDelete(id: number, name: string) {
  deleteTargetId.value = id
  deleteAccName.value = name
  showDeleteConfirm.value = true
}

async function doDeleteAccount() {
  if (!deleteTargetId.value) return
  await axios.delete(`/api/v1/accounts/${deleteTargetId.value}`)
  message.success('账号已删除')
  deleteTargetId.value = null
  await loadAccounts()
}

onMounted(loadAccounts)
</script>

<style scoped>
/* ── 筛选栏 ── */
.filter-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.filter-group { display: flex; gap: 10px; }
.filter-select {
  padding: 7px 12px; border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--bg-card); font-size: 13px; font-family: var(--font-body); color: var(--text-primary); outline: none;
}
.add-btn {
  padding: 8px 18px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500;
  background: linear-gradient(135deg, var(--accent-copper), #B88560); color: var(--text-inverse);
  border: none; cursor: pointer; font-family: var(--font-body); transition: all 0.2s;
}
.add-btn:hover { box-shadow: 0 2px 8px rgba(200,149,108,0.3); transform: translateY(-1px); }

/* ── 卡片网格 ── */
.account-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 18px; }
.account-card {
  background: var(--bg-card); border-radius: var(--radius-md); border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm); overflow: hidden; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  opacity: 0; transform: translateY(16px); animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.account-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.card-top-bar { height: 3px; }
.bar-green { background: linear-gradient(90deg, var(--accent-green), var(--accent-green-light)); }
.bar-amber { background: linear-gradient(90deg, var(--accent-amber), var(--accent-amber-light)); }
.bar-red { background: linear-gradient(90deg, var(--accent-red), var(--accent-red-light)); }
.card-body { padding: 20px; }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }

.platform-tag { padding: 3px 10px; border-radius: var(--radius-pill); font-size: 11px; font-weight: 500; background: var(--bg-subtle); color: var(--text-secondary); }
.status-badge { display: inline-flex; align-items: center; gap: 5px; padding: 3px 10px; border-radius: var(--radius-pill); font-size: 11px; font-weight: 550; }
.status-active { background: var(--accent-green-bg); color: var(--accent-green); }
.status-inactive { background: var(--accent-amber-bg); color: var(--accent-amber); }
.status-disabled { background: var(--accent-red-bg); color: var(--accent-red); }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

.shop-name { font-family: var(--font-display); font-size: 17px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px; }
.info-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.info-label { font-size: 12px; color: var(--text-tertiary); font-weight: 500; }
.info-value { font-family: var(--font-mono); font-size: 12.5px; color: var(--text-secondary); }

/* ── 验证码转发标签 ── */
.captcha-badge-row { margin-bottom: 12px; }
.captcha-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 10px; border-radius: var(--radius-pill); font-size: 11px; font-weight: 500;
}
.captcha-on { background: var(--accent-blue-bg); color: var(--accent-blue); }
.captcha-off { background: var(--bg-subtle); color: var(--text-tertiary); }
.captcha-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

/* ── 健康分 ── */
.health-section { margin-bottom: 16px; }
.health-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.health-score { font-family: var(--font-mono); font-size: 13px; font-weight: 600; }
.score-good { color: var(--accent-green); }
.score-warn { color: var(--accent-amber); }
.score-bad { color: var(--accent-red); }
.health-bar-wrap { height: 6px; background: var(--bg-subtle); border-radius: var(--radius-pill); overflow: hidden; }
.health-bar { height: 100%; border-radius: var(--radius-pill); transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1); }

.card-footer { display: flex; align-items: center; justify-content: space-between; }
.create-time { font-size: 11.5px; color: var(--text-tertiary); }
.footer-actions { display: flex; gap: 6px; }
.edit-btn, .delete-btn {
  padding: 4px 14px; border-radius: 6px; font-size: 12px; font-weight: 500;
  border: 1px solid var(--border); background: var(--bg-card); cursor: pointer;
  transition: all 0.2s; font-family: var(--font-body);
}
.edit-btn { color: var(--text-secondary); }
.edit-btn:hover { border-color: var(--accent-copper-light); color: var(--accent-copper); }
.delete-btn { color: var(--accent-red); border-color: var(--accent-red-light); }
.delete-btn:hover { background: var(--accent-red); color: white; border-color: var(--accent-red); }

/* ════════ 弹窗 ════════ */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(45,42,38,0.3); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.modal-card {
  background: var(--bg-card); border-radius: var(--radius-lg); padding: 28px 32px;
  width: 480px; max-width: 92vw; max-height: 85vh; overflow-y: auto;
  box-shadow: var(--shadow-lg); animation: fadeUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.modal-title { font-family: var(--font-display); font-size: 18px; font-weight: 600; margin-bottom: 20px; color: var(--text-primary); }
.form-group { margin-bottom: 16px; }
.form-label { display: block; font-size: 12.5px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px; }
.form-input {
  width: 100%; padding: 9px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--bg-base); font-size: 13px; font-family: var(--font-body); color: var(--text-primary); outline: none;
}
.form-input:focus { border-color: var(--accent-copper); }
.form-input:disabled { opacity: 0.5; cursor: not-allowed; }
.form-row { display: flex; gap: 12px; }
.flex1 { flex: 1; }

/* ── 验证码折叠区 ── */
.captcha-section {
  margin: 20px 0 8px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 14px; cursor: pointer; background: var(--bg-subtle);
  transition: background 0.15s;
}
.section-header:hover { background: var(--bg-hover); }
.section-title { font-size: 13px; font-weight: 550; color: var(--text-primary); }
.section-toggle { font-size: 12px; color: var(--accent-copper); font-weight: 500; }
.section-body { padding: 16px 14px 8px; }
.captcha-hint { font-size: 12.5px; color: var(--text-tertiary); line-height: 1.6; padding: 8px 0; }

/* ── Toggle 开关 ── */
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
.toggle-label { font-size: 12px; color: var(--text-secondary); }

/* ── 底部按钮 ── */
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }
.modal-btn {
  padding: 8px 20px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500;
  cursor: pointer; font-family: var(--font-body); transition: all 0.2s;
}
.modal-btn.cancel { background: var(--bg-subtle); border: 1px solid var(--border); color: var(--text-secondary); }
.modal-btn.cancel:hover { border-color: var(--text-tertiary); }
.modal-btn.confirm { background: linear-gradient(135deg, var(--accent-copper), #B88560); border: none; color: var(--text-inverse); }
.modal-btn.confirm:hover { box-shadow: 0 2px 8px rgba(200,149,108,0.3); }
</style>
