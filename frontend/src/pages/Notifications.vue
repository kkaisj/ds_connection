<!--
  消息通知页面
  卡片式展示通知配置，支持新增/编辑/删除（自定义确认弹窗）。
  展示通知策略（触发条件、频控参数）和启用状态。
-->
<template>
  <div class="notifications-page">
    <div class="card-grid">
      <div v-for="(n, i) in notifications" :key="n.id" class="notify-card" :style="{ animationDelay: `${0.05 * i}s` }">
        <div class="card-body">
          <div class="card-header">
            <div class="channel-icon" :class="`icon-${getChannelColor(n.channel)}`">{{ channelIcon(n.channel) }}</div>
            <span class="status-badge" :class="`status-${n.status}`">{{ n.status === 'active' ? '启用' : '停用' }}</span>
          </div>
          <h3 class="channel-name">{{ channelLabel(n.channel) }}</h3>
          <div class="strategy-list">
            <div class="strategy-item">
              <span class="strategy-dot" :class="n.notify_on_fail ? 'dot-on' : 'dot-off'"></span><span>失败通知</span>
            </div>
            <div class="strategy-item">
              <span class="strategy-dot" :class="n.notify_on_retry_fail ? 'dot-on' : 'dot-off'"></span><span>重试失败通知</span>
            </div>
            <div class="strategy-item">
              <span class="strategy-dot" :class="n.notify_on_account_invalid ? 'dot-on' : 'dot-off'"></span><span>账号失效通知</span>
            </div>
          </div>
          <div class="rate-info">
            <span class="rate-item">去重窗口: {{ n.dedupe_window_sec }}s</span>
            <span class="rate-item">频控: {{ n.rate_limit_per_min }}/min</span>
          </div>
          <div class="card-footer">
            <span class="create-time">{{ formatDate(n.created_at) }}</span>
            <div class="footer-actions">
              <button class="edit-btn" @click="openEdit(n)">编辑</button>
              <button class="delete-btn" @click="confirmDelete(n.id, n.channel)">删除</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 新增卡片 -->
      <div class="notify-card add-card" @click="openCreate">
        <div class="add-body">
          <span class="add-icon">+</span>
          <span class="add-text">添加通知配置</span>
        </div>
      </div>
    </div>

    <!-- ════════ 新增/编辑弹窗 ════════ -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">{{ isEdit ? '编辑通知配置' : '新增通知配置' }}</h3>
          <button class="modal-close" @click="showModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">通知通道</label>
            <DcSelect v-model="form.channel" :options="channelOptions" :disabled="isEdit" />
          </div>
          <div v-if="!isEdit" class="form-group">
            <label class="form-label required">Webhook URL</label>
            <input v-model="form.webhook_url" class="form-input" placeholder="https://open.feishu.cn/..." />
          </div>

          <!-- 通知策略开关 -->
          <div class="form-section-title">通知策略</div>
          <div class="toggle-group">
            <div class="toggle-item">
              <span class="toggle-label">失败通知</span>
              <button class="toggle-btn" :class="form.notify_on_fail ? 'toggle-on' : 'toggle-off'" @click="form.notify_on_fail = !form.notify_on_fail">
                <span class="toggle-knob"></span>
              </button>
            </div>
            <div class="toggle-item">
              <span class="toggle-label">重试失败通知</span>
              <button class="toggle-btn" :class="form.notify_on_retry_fail ? 'toggle-on' : 'toggle-off'" @click="form.notify_on_retry_fail = !form.notify_on_retry_fail">
                <span class="toggle-knob"></span>
              </button>
            </div>
            <div class="toggle-item">
              <span class="toggle-label">账号失效通知</span>
              <button class="toggle-btn" :class="form.notify_on_account_invalid ? 'toggle-on' : 'toggle-off'" @click="form.notify_on_account_invalid = !form.notify_on_account_invalid">
                <span class="toggle-knob"></span>
              </button>
            </div>
          </div>

          <!-- 频控参数 -->
          <div class="form-section-title">频控设置</div>
          <div class="form-row">
            <div class="form-group flex1">
              <label class="form-label">去重窗口（秒）</label>
              <input v-model.number="form.dedupe_window_sec" class="form-input" type="number" />
            </div>
            <div class="form-group flex1">
              <label class="form-label">频控上限（条/分钟）</label>
              <input v-model.number="form.rate_limit_per_min" class="form-input" type="number" />
            </div>
          </div>

          <!-- 编辑时显示状态切换 -->
          <div v-if="isEdit" class="form-group">
            <label class="form-label">状态</label>
            <DcSelect v-model="form.status" :options="statusOptions" />
          </div>
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
      :desc="`确定要删除「${channelLabel(deleteName)}」通知配置吗？删除后不可恢复。`"
      confirm-text="删除"
      :danger="true"
      @confirm="doDelete"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 消息通知页面逻辑
 * - 卡片展示通知配置，含策略开关和频控参数
 * - 新增/编辑弹窗，编辑时支持修改策略和状态
 * - 自定义确认弹窗删除
 */
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'
import DcSelect from '@/components/DcSelect.vue'
import DcConfirm from '@/components/DcConfirm.vue'

const message = useMessage()

/* ── 类型 ── */
interface NotifyItem {
  id: number; channel: string; notify_on_fail: boolean; notify_on_retry_fail: boolean;
  notify_on_account_invalid: boolean; dedupe_window_sec: number; rate_limit_per_min: number;
  status: string; created_at: string | null
}

/* ── 状态 ── */
const notifications = ref<NotifyItem[]>([])
const showModal = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)

/* ── 删除确认 ── */
const showDeleteConfirm = ref(false)
const deleteTargetId = ref<number | null>(null)
const deleteName = ref('')

/* ── 下拉选项 ── */
const channelOptions = [
  { value: 'feishu', label: '飞书 Webhook' },
  { value: 'dingtalk', label: '钉钉 Webhook' },
  { value: 'wechat_work', label: '企业微信 Webhook' },
]
const statusOptions = [
  { value: 'active', label: '启用' },
  { value: 'inactive', label: '停用' },
]

/* ── 表单 ── */
const defaultForm = () => ({
  channel: 'feishu',
  webhook_url: '',
  notify_on_fail: true,
  notify_on_retry_fail: true,
  notify_on_account_invalid: true,
  dedupe_window_sec: 300,
  rate_limit_per_min: 20,
  status: 'active',
})
const form = ref(defaultForm())

/* ── 工具函数 ── */
const channelLabels: Record<string, string> = { feishu: '飞书 Webhook', dingtalk: '钉钉 Webhook', wechat_work: '企业微信 Webhook' }
function channelLabel(c: string) { return channelLabels[c] || c }
function channelIcon(c: string) { return c === 'feishu' ? '飞' : c === 'dingtalk' ? '钉' : '企' }
function getChannelColor(c: string) { return c === 'feishu' ? 'blue' : c === 'dingtalk' ? 'copper' : 'green' }
function formatDate(iso: string | null) { return iso ? iso.split('T')[0] : '--' }

/* ── 数据加载 ── */
async function loadNotifications() {
  const res = await axios.get('/api/v1/notifications')
  notifications.value = res.data.data
}

/* ── 新增 ── */
function openCreate() {
  isEdit.value = false
  editId.value = null
  form.value = defaultForm()
  showModal.value = true
}

/* ── 编辑（回填数据） ── */
function openEdit(n: NotifyItem) {
  isEdit.value = true
  editId.value = n.id
  form.value = {
    channel: n.channel,
    webhook_url: '',
    notify_on_fail: n.notify_on_fail,
    notify_on_retry_fail: n.notify_on_retry_fail,
    notify_on_account_invalid: n.notify_on_account_invalid,
    dedupe_window_sec: n.dedupe_window_sec,
    rate_limit_per_min: n.rate_limit_per_min,
    status: n.status,
  }
  showModal.value = true
}

/* ── 提交（新增或编辑） ── */
async function submitForm() {
  if (isEdit.value && editId.value) {
    const body: Record<string, unknown> = {
      notify_on_fail: form.value.notify_on_fail,
      notify_on_retry_fail: form.value.notify_on_retry_fail,
      notify_on_account_invalid: form.value.notify_on_account_invalid,
      dedupe_window_sec: form.value.dedupe_window_sec,
      rate_limit_per_min: form.value.rate_limit_per_min,
      status: form.value.status,
    }
    if (form.value.webhook_url) body.webhook_url = form.value.webhook_url
    await axios.patch(`/api/v1/notifications/${editId.value}`, body)
    message.success('通知配置已更新')
  } else {
    if (!form.value.webhook_url) { message.warning('请输入 Webhook URL'); return }
    await axios.post('/api/v1/notifications', {
      channel: form.value.channel,
      webhook_url: form.value.webhook_url,
      notify_on_fail: form.value.notify_on_fail,
      notify_on_retry_fail: form.value.notify_on_retry_fail,
      notify_on_account_invalid: form.value.notify_on_account_invalid,
      dedupe_window_sec: form.value.dedupe_window_sec,
      rate_limit_per_min: form.value.rate_limit_per_min,
    })
    message.success('通知配置已创建')
  }
  showModal.value = false
  await loadNotifications()
}

/* ── 确认删除 ── */
function confirmDelete(id: number, channel: string) {
  deleteTargetId.value = id
  deleteName.value = channel
  showDeleteConfirm.value = true
}

async function doDelete() {
  if (!deleteTargetId.value) return
  await axios.delete(`/api/v1/notifications/${deleteTargetId.value}`)
  message.success('通知配置已删除')
  deleteTargetId.value = null
  await loadNotifications()
}

onMounted(loadNotifications)
</script>

<style scoped>
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 18px; }
.notify-card {
  background: var(--bg-card); border-radius: var(--radius-md); border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  opacity: 0; transform: translateY(16px); animation: fadeUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.notify-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.card-body { padding: 22px; }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.channel-icon {
  width: 40px; height: 40px; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 600;
}
.icon-blue { background: var(--accent-blue-bg); color: var(--accent-blue); }
.icon-copper { background: var(--accent-copper-bg); color: var(--accent-copper); }
.icon-green { background: var(--accent-green-bg); color: var(--accent-green); }
.status-badge { padding: 3px 10px; border-radius: var(--radius-pill); font-size: 11px; font-weight: 550; }
.status-active { background: var(--accent-green-bg); color: var(--accent-green); }
.status-inactive { background: var(--accent-amber-bg); color: var(--accent-amber); }
.channel-name { font-family: var(--font-display); font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 14px; }

.strategy-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 14px; }
.strategy-item { display: flex; align-items: center; gap: 8px; font-size: 12.5px; color: var(--text-secondary); }
.strategy-dot { width: 7px; height: 7px; border-radius: 50%; }
.dot-on { background: var(--accent-green); }
.dot-off { background: var(--border); }

.rate-info { display: flex; gap: 16px; margin-bottom: 16px; }
.rate-item { font-family: var(--font-mono); font-size: 11.5px; color: var(--text-tertiary); }

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
.add-body { padding: 22px; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 200px; gap: 8px; }
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
.modal-header {
  display: flex; align-items: center; justify-content: space-between; padding: 22px 28px 0;
}
.modal-title { font-family: var(--font-display); font-size: 18px; font-weight: 600; color: var(--text-primary); }
.modal-close {
  background: none; border: none; font-size: 22px; color: var(--text-tertiary);
  cursor: pointer; padding: 4px 8px; border-radius: 4px; transition: all 0.15s; line-height: 1;
}
.modal-close:hover { background: var(--bg-subtle); color: var(--text-primary); }
.modal-body { padding: 20px 28px; overflow-y: auto; flex: 1; }

.form-group { margin-bottom: 16px; }
.form-label { display: block; font-size: 13px; font-weight: 500; color: var(--text-secondary); margin-bottom: 6px; }
.form-label.required::before { content: '* '; color: var(--accent-red); }
.form-input {
  width: 100%; padding: 9px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--bg-base); font-size: 13px; font-family: var(--font-body); color: var(--text-primary); outline: none;
}
.form-input:focus { border-color: var(--accent-copper); }
.form-row { display: flex; gap: 12px; }
.flex1 { flex: 1; }

/* 表单分区标题 */
.form-section-title {
  font-size: 13px; font-weight: 600; color: var(--text-primary); margin: 20px 0 12px;
  padding-bottom: 8px; border-bottom: 1px solid var(--border-light);
}

/* Toggle 开关组 */
.toggle-group { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
.toggle-item { display: flex; align-items: center; justify-content: space-between; }
.toggle-label { font-size: 13px; color: var(--text-secondary); }
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
.modal-btn.confirm { background: var(--accent-copper); border: none; color: white; }
.modal-btn.confirm:hover { opacity: 0.9; }
</style>
