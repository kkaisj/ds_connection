<!--
  DcSelect 自定义下拉选择器
  替代浏览器原生 select，统一设计风格。
  支持 v-model 双向绑定、placeholder、禁用状态。

  用法:
  <DcSelect v-model="value" :options="[{value:'a', label:'选项A'}]" placeholder="请选择" />
-->
<template>
  <div
    class="dc-select"
    :class="{ open: isOpen, disabled }"
    ref="selectRef"
  >
    <!-- 触发区域 -->
    <div class="dc-select-trigger" @click="toggle">
      <span class="dc-select-value" :class="{ placeholder: !selectedLabel }">
        {{ selectedLabel || placeholder }}
      </span>
      <span class="dc-select-arrow" :class="{ flipped: isOpen }">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </span>
    </div>

    <!-- 下拉面板 -->
    <Teleport to="body">
      <div
        v-if="isOpen"
        class="dc-select-dropdown"
        :style="dropdownStyle"
        ref="dropdownRef"
      >
        <div
          v-for="opt in options"
          :key="opt.value"
          class="dc-select-option"
          :class="{ active: modelValue === opt.value }"
          @click="select(opt.value)"
        >
          <span class="option-label">{{ opt.label }}</span>
          <span v-if="modelValue === opt.value" class="option-check">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </span>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
/**
 * 自定义下拉选择器
 * - Teleport 到 body 避免被父容器 overflow 裁剪
 * - 点击外部自动关闭
 * - 选中项显示勾选图标
 */
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'

interface Option {
  value: string | number
  label: string
}

const props = withDefaults(defineProps<{
  modelValue: string | number
  options: Option[]
  placeholder?: string
  disabled?: boolean
}>(), {
  placeholder: '请选择',
  disabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  change: [value: string | number]
}>()

const isOpen = ref(false)
const selectRef = ref<HTMLElement>()
const dropdownRef = ref<HTMLElement>()
const dropdownStyle = ref<Record<string, string>>({})

/* ── 当前选中项的 label ── */
const selectedLabel = computed(() => {
  const opt = props.options.find(o => o.value === props.modelValue)
  return opt?.label || ''
})

/* ── 计算下拉面板位置（相对于触发器） ── */
function updatePosition() {
  if (!selectRef.value) return
  const rect = selectRef.value.getBoundingClientRect()
  dropdownStyle.value = {
    position: 'fixed',
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
    width: `${rect.width}px`,
    zIndex: '9999',
  }
}

/* ── 打开/关闭 ── */
function toggle() {
  if (props.disabled) return
  if (isOpen.value) {
    isOpen.value = false
    return
  }
  // 先计算一次位置再打开，避免首次打开时面板短暂错位。
  updatePosition()
  isOpen.value = true
  nextTick(updatePosition)
}

/* ── 选择 ── */
function select(value: string | number) {
  emit('update:modelValue', value)
  emit('change', value)
  isOpen.value = false
}

/* ── 点击外部关闭 ── */
function handleClickOutside(e: MouseEvent) {
  const target = e.target as Node
  if (
    selectRef.value && !selectRef.value.contains(target) &&
    dropdownRef.value && !dropdownRef.value.contains(target)
  ) {
    isOpen.value = false
  }
}

/** 下拉展开时，窗口尺寸或滚动变化都需要重算定位，避免面板漂移。 */
function handleViewportChange() {
  if (!isOpen.value) return
  updatePosition()
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside)
  window.addEventListener('resize', handleViewportChange)
  window.addEventListener('scroll', handleViewportChange, true)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside)
  window.removeEventListener('resize', handleViewportChange)
  window.removeEventListener('scroll', handleViewportChange, true)
})
</script>

<style scoped>
.dc-select {
  position: relative;
  display: inline-flex;
  min-width: 120px;
}

.dc-select.disabled { opacity: 0.5; pointer-events: none; }

/* ── 触发器 ── */
.dc-select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-card);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.dc-select.open .dc-select-trigger,
.dc-select-trigger:hover {
  border-color: var(--accent-copper);
  box-shadow: 0 0 0 2px rgba(200, 149, 108, 0.1);
}

.dc-select-value {
  font-size: 13px;
  font-family: var(--font-body);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dc-select-value.placeholder {
  color: var(--text-tertiary);
}

.dc-select-arrow {
  display: flex;
  align-items: center;
  color: var(--text-tertiary);
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.dc-select-arrow.flipped {
  transform: rotate(180deg);
}
</style>

<!-- 下拉面板用全局样式（因为 Teleport 到 body） -->
<style>
.dc-select-dropdown {
  background: var(--bg-base, #FDFBF7);
  border: 1px solid var(--border, #E8E3DC);
  border-radius: 8px;
  box-shadow: 0 8px 30px rgba(45, 42, 38, 0.12), 0 2px 8px rgba(45, 42, 38, 0.06);
  padding: 4px;
  max-height: 240px;
  overflow-y: auto;
  animation: dcDropIn 0.15s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes dcDropIn {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.dc-select-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.12s;
  user-select: none;
}

.dc-select-option:hover {
  background: var(--select-option-hover, #F7F1E8);
}

.dc-select-option.active {
  background: var(--accent-copper-bg, #FDF6EF);
}

.dc-select-option .option-label {
  font-size: 13px;
  font-family: var(--font-body, 'DM Sans', -apple-system, sans-serif);
  color: var(--text-primary, #2D2A26);
}

.dc-select-option.active .option-label {
  color: var(--accent-copper, #C8956C);
  font-weight: 550;
}

.dc-select-option .option-check {
  color: var(--accent-copper, #C8956C);
  display: flex;
  align-items: center;
}

/* 滚动条 */
.dc-select-dropdown::-webkit-scrollbar { width: 4px; }
.dc-select-dropdown::-webkit-scrollbar-track { background: transparent; }
.dc-select-dropdown::-webkit-scrollbar-thumb { background: #E8E3DC; border-radius: 2px; }
</style>
