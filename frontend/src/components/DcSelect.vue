<template>
  <div class="dc-select" :class="{ open: isOpen, disabled }" ref="selectRef">
    <div class="dc-select-trigger" @click="toggle">
      <span class="dc-select-value" :class="{ placeholder: !selectedLabel }">
        {{ selectedLabel || placeholder }}
      </span>
      <span class="dc-select-arrow" :class="{ flipped: isOpen }">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </span>
    </div>

    <Teleport to="body">
      <div
        v-if="isOpen"
        class="dc-select-dropdown"
        :style="dropdownStyle"
        ref="dropdownRef"
        @scroll="handleDropdownScroll"
      >
        <div v-if="searchable" class="dc-select-search-wrap">
          <input
            v-model="keyword"
            class="dc-select-search"
            :placeholder="searchPlaceholder"
            @input="onKeywordInput"
          />
        </div>

        <div
          v-for="opt in filteredOptions"
          :key="opt.value"
          class="dc-select-option"
          :class="{ active: modelValue === opt.value }"
          @click="select(opt.value)"
        >
          <span class="option-label">{{ opt.label }}</span>
          <span v-if="modelValue === opt.value" class="option-check">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </span>
        </div>

        <div v-if="loading" class="dc-select-loading">加载中...</div>
        <div v-if="!loading && filteredOptions.length === 0" class="dc-select-empty">暂无可选项</div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'

interface Option {
  value: string | number
  label: string
}

const props = withDefaults(
  defineProps<{
    modelValue: string | number
    options: Option[]
    placeholder?: string
    disabled?: boolean
    searchable?: boolean
    searchPlaceholder?: string
    remoteSearch?: boolean
    loading?: boolean
  }>(),
  {
    placeholder: '请选择',
    disabled: false,
    searchable: false,
    searchPlaceholder: '请输入关键字搜索',
    remoteSearch: false,
    loading: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  change: [value: string | number]
  search: [keyword: string]
  reachEnd: []
}>()

const isOpen = ref(false)
const selectRef = ref<HTMLElement>()
const dropdownRef = ref<HTMLElement>()
const dropdownStyle = ref<Record<string, string>>({})
const keyword = ref('')

const selectedLabel = computed(() => {
  const opt = props.options.find((o) => o.value === props.modelValue)
  return opt?.label || ''
})

const filteredOptions = computed(() => {
  if (!props.searchable) return props.options
  if (props.remoteSearch) return props.options
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return props.options
  return props.options.filter((opt) => opt.label.toLowerCase().includes(kw))
})

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

function toggle() {
  if (props.disabled) return
  if (isOpen.value) {
    isOpen.value = false
    return
  }
  updatePosition()
  isOpen.value = true
  keyword.value = ''
  emit('search', '')
  nextTick(updatePosition)
}

function select(value: string | number) {
  emit('update:modelValue', value)
  emit('change', value)
  isOpen.value = false
}

function onKeywordInput() {
  emit('search', keyword.value.trim())
}

function handleDropdownScroll(e: Event) {
  const target = e.target as HTMLElement
  const threshold = 24
  if (target.scrollHeight - target.scrollTop - target.clientHeight <= threshold) {
    emit('reachEnd')
  }
}

function handleClickOutside(e: MouseEvent) {
  const target = e.target as Node
  if (
    selectRef.value &&
    !selectRef.value.contains(target) &&
    dropdownRef.value &&
    !dropdownRef.value.contains(target)
  ) {
    isOpen.value = false
  }
}

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

.dc-select.disabled {
  opacity: 0.5;
  pointer-events: none;
}

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

<style>
.dc-select-dropdown {
  background: var(--bg-base, #fdfbf7);
  border: 1px solid var(--border, #e8e3dc);
  border-radius: 8px;
  box-shadow: 0 8px 30px rgba(45, 42, 38, 0.12), 0 2px 8px rgba(45, 42, 38, 0.06);
  padding: 4px;
  max-height: 240px;
  overflow-y: auto;
  animation: dcDropIn 0.15s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes dcDropIn {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dc-select-search-wrap {
  position: sticky;
  top: -4px;
  z-index: 1;
  padding: 6px;
  margin: -4px -4px 4px;
  background: var(--bg-base, #fdfbf7);
  border-bottom: 1px solid var(--border-light, #eee8e0);
}

.dc-select-search {
  width: 100%;
  border: 1px solid var(--border, #e8e3dc);
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}

.dc-select-search:focus {
  border-color: var(--accent-copper, #c8956c);
  box-shadow: 0 0 0 2px rgba(200, 149, 108, 0.1);
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
  background: var(--select-option-hover, #f7f1e8);
}

.dc-select-option.active {
  background: var(--accent-copper-bg, #fdf6ef);
}

.dc-select-option .option-label {
  font-size: 13px;
  font-family: var(--font-body, 'DM Sans', -apple-system, sans-serif);
  color: var(--text-primary, #2d2a26);
}

.dc-select-option.active .option-label {
  color: var(--accent-copper, #c8956c);
  font-weight: 550;
}

.dc-select-option .option-check {
  color: var(--accent-copper, #c8956c);
  display: flex;
  align-items: center;
}

.dc-select-empty {
  padding: 10px 12px;
  color: var(--text-tertiary, #a49a8d);
  font-size: 12px;
}

.dc-select-loading {
  padding: 10px 12px;
  color: var(--text-secondary, #7a7268);
  font-size: 12px;
}

.dc-select-dropdown::-webkit-scrollbar {
  width: 4px;
}

.dc-select-dropdown::-webkit-scrollbar-track {
  background: transparent;
}

.dc-select-dropdown::-webkit-scrollbar-thumb {
  background: #e8e3dc;
  border-radius: 2px;
}
</style>
