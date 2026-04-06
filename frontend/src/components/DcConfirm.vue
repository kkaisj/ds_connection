<!--
  DcConfirm 自定义确认弹窗
  替代浏览器原生 confirm，统一设计风格。
  支持标题、描述文本、确认/取消按钮、危险模式。

  用法:
  <DcConfirm v-model:show="visible" title="确认删除？" desc="删除后不可恢复" @confirm="doDelete" />
-->
<template>
  <Teleport to="body">
    <Transition name="dc-confirm">
      <div v-if="show" class="confirm-overlay" @click.self="cancel">
        <div class="confirm-card">
          <!-- 图标 -->
          <div class="confirm-icon" :class="danger ? 'icon-danger' : 'icon-info'">
            <svg v-if="danger" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>

          <h3 class="confirm-title">{{ title }}</h3>
          <p v-if="desc" class="confirm-desc">{{ desc }}</p>

          <div class="confirm-actions">
            <button class="confirm-btn btn-cancel" @click="cancel">取消</button>
            <button class="confirm-btn" :class="danger ? 'btn-danger' : 'btn-primary'" @click="confirm">
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 自定义确认弹窗
 * - v-model:show 控制显隐
 * - danger 模式下按钮为红色
 * - emit confirm / cancel 事件
 */
withDefaults(defineProps<{
  show: boolean
  title?: string
  desc?: string
  confirmText?: string
  danger?: boolean
}>(), {
  title: '确认操作',
  desc: '',
  confirmText: '确认',
  danger: true,
})

const emit = defineEmits<{
  'update:show': [val: boolean]
  confirm: []
  cancel: []
}>()

function cancel() {
  emit('update:show', false)
  emit('cancel')
}

function confirm() {
  emit('update:show', false)
  emit('confirm')
}
</script>

<style scoped>
.confirm-overlay {
  position: fixed; inset: 0; z-index: 10000;
  background: rgba(45,42,38,0.35); backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
}

.confirm-card {
  background: var(--bg-card, #fff); border-radius: 16px;
  padding: 28px 32px 24px; width: 380px; max-width: 90vw;
  box-shadow: 0 16px 48px rgba(45,42,38,0.15);
  text-align: center;
}

.confirm-icon {
  width: 48px; height: 48px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 16px;
}

.icon-danger { background: var(--accent-red-bg, #FDF2F0); color: var(--accent-red, #C75C4A); }
.icon-info { background: var(--accent-blue-bg, #F0F5FA); color: var(--accent-blue, #5B7FA6); }

.confirm-title {
  font-family: var(--font-display, Georgia); font-size: 17px; font-weight: 600;
  color: var(--text-primary, #2D2A26); margin-bottom: 8px;
}

.confirm-desc {
  font-size: 13px; color: var(--text-tertiary, #A39E98); line-height: 1.5;
  margin-bottom: 24px;
}

.confirm-actions { display: flex; gap: 10px; justify-content: center; margin-top: 20px; }

.confirm-btn {
  padding: 8px 24px; border-radius: 8px; font-size: 13px; font-weight: 500;
  cursor: pointer; font-family: var(--font-body, sans-serif); transition: all 0.2s; border: none;
}

.btn-cancel {
  background: var(--bg-subtle, #F5F1EB); color: var(--text-secondary, #6B6560);
  border: 1px solid var(--border, #E8E3DC);
}
.btn-cancel:hover { border-color: var(--text-tertiary, #A39E98); }

.btn-danger { background: var(--accent-red, #C75C4A); color: white; }
.btn-danger:hover { opacity: 0.9; }

.btn-primary {
  background: linear-gradient(135deg, var(--accent-copper, #C8956C), #B88560);
  color: white;
}
.btn-primary:hover { box-shadow: 0 2px 8px rgba(200,149,108,0.3); }

/* 过渡动画 */
.dc-confirm-enter-active { transition: opacity 0.15s ease; }
.dc-confirm-enter-active .confirm-card { transition: transform 0.2s cubic-bezier(0.16,1,0.3,1), opacity 0.15s; }
.dc-confirm-leave-active { transition: opacity 0.1s ease; }
.dc-confirm-enter-from { opacity: 0; }
.dc-confirm-enter-from .confirm-card { transform: scale(0.95); opacity: 0; }
.dc-confirm-leave-to { opacity: 0; }
</style>
