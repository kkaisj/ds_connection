<template>
  <div class="dashboard">
    <!-- Stat Cards -->
    <div class="stats-row">
      <div
        v-for="(card, i) in statCards"
        :key="card.label"
        class="stat-card"
        :style="{ animationDelay: `${0.08 + i * 0.08}s` }"
      >
        <div class="stat-top-bar" :class="`bar-${card.color}`"></div>
        <div class="stat-header">
          <span class="stat-label">{{ card.label }}</span>
          <div class="stat-icon-wrap" :class="`icon-${card.color}`">
            <component :is="card.icon" />
          </div>
        </div>
        <div class="stat-value">
          {{ card.displayValue }}{{ card.suffix || '' }}
        </div>
        <div class="stat-footer">
          <span class="stat-trend" :class="card.trendClass">
            {{ card.trendPrefix }}{{ card.trendValue }}
          </span>
          <span>{{ card.trendLabel }}</span>
        </div>
      </div>
    </div>

    <!-- Charts -->
    <div class="charts-row">
      <div class="card" style="animation-delay: 0.38s;">
        <div class="card-header">
          <span class="card-title">执行趋势</span>
          <div class="card-actions">
            <button
              v-for="opt in ['7日', '30日']"
              :key="opt"
              class="card-action-btn"
              :class="{ active: trendRange === opt }"
              @click="trendRange = opt"
            >{{ opt }}</button>
          </div>
        </div>
        <div ref="trendChartRef" class="chart-container"></div>
      </div>

      <div class="card" style="animation-delay: 0.44s;">
        <div class="card-header">
          <span class="card-title">平台分布</span>
        </div>
        <div ref="platformChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- Recent Runs Table -->
    <div class="card table-card" style="animation-delay: 0.5s;">
      <div class="card-header" style="padding-bottom: 4px;">
        <span class="card-title">最近执行</span>
        <div class="card-actions">
          <button class="card-action-btn">全部状态</button>
          <button class="card-action-btn">查看更多</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>任务</th>
              <th>平台</th>
              <th>店铺</th>
              <th>状态</th>
              <th>耗时</th>
              <th>执行时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in recentRuns" :key="run.task_key + run.started_at">
              <td>
                <div class="cell-task">
                  <div class="task-icon-sm" :class="`icon-${getRunColor(run)}`">
                    {{ run.task_name[0] }}
                  </div>
                  <div>
                    <div class="task-name">{{ run.task_name }}</div>
                    <div class="task-sub">{{ run.task_key }}</div>
                  </div>
                </div>
              </td>
              <td><span class="platform-tag">{{ run.platform }}</span></td>
              <td>{{ run.shop }}</td>
              <td>
                <span class="status-badge" :class="`status-${run.status}`">
                  <span class="status-dot"></span>
                  {{ statusLabel(run.status) }}
                </span>
              </td>
              <td class="cell-mono">{{ formatDuration(run.duration_ms) }}</td>
              <td class="cell-time">{{ formatTime(run.started_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Bottom Row -->
    <div class="bottom-row">
      <!-- Account Health -->
      <div class="card" style="animation-delay: 0.56s;">
        <div class="card-header">
          <span class="card-title">账号健康度</span>
          <div class="card-actions">
            <button class="card-action-btn">共 {{ health?.total || 0 }} 个账号</button>
          </div>
        </div>
        <div class="health-list">
          <div v-for="bar in healthBars" :key="bar.label" class="health-item">
            <span class="health-label">{{ bar.label }}</span>
            <div class="health-bar-wrap">
              <div
                class="health-bar"
                :style="{ width: bar.width, background: bar.bg }"
              ></div>
            </div>
            <span class="health-value">{{ bar.value }}</span>
          </div>

          <div class="platform-status-section">
            <span class="section-label">平台连接状态</span>
            <div class="platform-tags">
              <div
                v-for="p in health?.platforms || []"
                :key="p.name"
                class="platform-status-tag"
                :class="`ps-${p.status}`"
              >
                <span class="ps-dot"></span>{{ p.name }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Todos -->
      <div class="card" style="animation-delay: 0.62s;">
        <div class="card-header">
          <span class="card-title">待处理事项</span>
          <div class="card-actions">
            <button class="card-action-btn" style="color: var(--accent-red);">
              {{ todos.length }} 项待办
            </button>
          </div>
        </div>
        <div class="todo-list">
          <div v-for="(todo, i) in todos" :key="i" class="todo-item">
            <span class="todo-priority" :class="`priority-${todo.priority}`"></span>
            <span class="todo-text">{{ todo.text }}</span>
            <span class="todo-tag" :class="tagClass(todo.tag)">{{ todo.tag }}</span>
            <span class="todo-time">{{ todo.time }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, h } from 'vue'
import * as echarts from 'echarts'
import {
  BarChartOutline,
  CheckmarkCircleOutline,
  PulseOutline,
  WarningOutline,
} from '@vicons/ionicons5'
import {
  dashboardApi,
  type DashboardStats,
  type TrendData,
  type PlatformItem,
  type RecentRun,
  type HealthData,
  type TodoItem,
} from '@/api/dashboard'

// ── State ──
const stats = ref<DashboardStats | null>(null)
const trend = ref<TrendData | null>(null)
const platforms = ref<PlatformItem[]>([])
const recentRuns = ref<RecentRun[]>([])
const health = ref<HealthData | null>(null)
const todos = ref<TodoItem[]>([])
const trendRange = ref('7日')

// ── Chart refs ──
const trendChartRef = ref<HTMLDivElement>()
const platformChartRef = ref<HTMLDivElement>()
let trendChartInstance: echarts.ECharts | null = null
let platformChartInstance: echarts.ECharts | null = null

// ── Count-up animation ──
const animatedValues = ref<Record<string, number>>({
  active_tasks: 0,
  today_success: 0,
  success_rate_7d: 0,
  alert_count: 0,
})

function animateCountUp(key: string, target: number, isFloat = false) {
  const duration = 1200
  const start = performance.now()
  function tick(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    animatedValues.value[key] = isFloat
      ? parseFloat((eased * target).toFixed(1))
      : Math.floor(eased * target)
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

// ── Stat cards ──
const statCards = computed(() => {
  const s = stats.value
  return [
    {
      label: '活跃任务',
      displayValue: animatedValues.value.active_tasks,
      suffix: '',
      icon: () => h(BarChartOutline),
      color: 'copper',
      trendClass: 'trend-up',
      trendPrefix: '+',
      trendValue: s?.active_tasks_delta ?? 0,
      trendLabel: '较上周',
    },
    {
      label: '今日成功',
      displayValue: animatedValues.value.today_success,
      suffix: '',
      icon: () => h(CheckmarkCircleOutline),
      color: 'green',
      trendClass: 'trend-up',
      trendPrefix: '+',
      trendValue: s?.today_success_delta ?? 0,
      trendLabel: '较昨日',
    },
    {
      label: '7日成功率',
      displayValue: animatedValues.value.success_rate_7d,
      suffix: '%',
      icon: () => h(PulseOutline),
      color: 'blue',
      trendClass: 'trend-up',
      trendPrefix: '+',
      trendValue: `${s?.success_rate_delta ?? 0}%`,
      trendLabel: '较上周',
    },
    {
      label: '异常告警',
      displayValue: animatedValues.value.alert_count,
      suffix: '',
      icon: () => h(WarningOutline),
      color: 'red',
      trendClass: 'trend-down',
      trendPrefix: '+',
      trendValue: 1,
      trendLabel: '需处理',
    },
  ]
})

// ── Health bars ──
const healthBars = computed(() => {
  const h = health.value
  if (!h) return []
  const total = h.total || 1
  return [
    { label: '健康', value: h.healthy, width: `${(h.healthy / total) * 100}%`, bg: 'var(--accent-green)' },
    { label: '警告', value: h.warning, width: `${(h.warning / total) * 100}%`, bg: 'var(--accent-amber)' },
    { label: '失效', value: h.invalid, width: `${(h.invalid / total) * 100}%`, bg: 'var(--accent-red)' },
  ]
})

// ── Helpers ──
const statusMap: Record<string, string> = {
  success: '成功',
  failed: '失败',
  running: '运行中',
  pending: '等待中',
}
function statusLabel(s: string) { return statusMap[s] || s }

const colorMap: Record<string, string> = {
  success: 'green',
  failed: 'red',
  running: 'blue',
  pending: 'amber',
}
function getRunColor(run: RecentRun) { return colorMap[run.status] || 'copper' }

function formatDuration(ms: number | null) {
  if (ms == null) return '--'
  return `${(ms / 1000).toFixed(1)}s`
}

function formatTime(iso: string) {
  return iso.split('T')[1]?.substring(0, 8) || iso
}

function tagClass(tag: string) {
  if (tag === '紧急') return 'tag-urgent'
  if (tag === '预警') return 'tag-warn'
  return 'tag-info'
}

// ── Charts ──
const chartColors = {
  green: '#4A7C6F',
  red: '#C75C4A',
  copper: '#C8956C',
  blue: '#5B7FA6',
  border: '#E8E3DC',
  textTertiary: '#A39E98',
}

function renderTrendChart() {
  if (!trendChartRef.value || !trend.value) return
  if (!trendChartInstance) {
    trendChartInstance = echarts.init(trendChartRef.value)
  }
  trendChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#FFFDF9',
      borderColor: chartColors.border,
      borderWidth: 1,
      textStyle: { color: '#2D2A26', fontFamily: 'DM Sans', fontSize: 12 },
    },
    legend: {
      top: 6, right: 0,
      itemWidth: 12, itemHeight: 3, itemGap: 16,
      textStyle: { color: chartColors.textTertiary, fontSize: 11, fontFamily: 'DM Sans' },
    },
    grid: { left: 12, right: 12, top: 40, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: trend.value.dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: chartColors.border } },
      axisTick: { show: false },
      axisLabel: { color: chartColors.textTertiary, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#F0ECE6', type: 'dashed' } },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: chartColors.textTertiary, fontSize: 11, fontFamily: 'JetBrains Mono' },
    },
    series: [
      {
        name: '成功', type: 'line', smooth: true,
        symbol: 'circle', symbolSize: 6,
        lineStyle: { color: chartColors.green, width: 2.5 },
        itemStyle: { color: chartColors.green, borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(74,124,111,0.15)' },
            { offset: 1, color: 'rgba(74,124,111,0.01)' },
          ]),
        },
        data: trend.value.success,
        animationDuration: 1200,
      },
      {
        name: '失败', type: 'line', smooth: true,
        symbol: 'circle', symbolSize: 6,
        lineStyle: { color: chartColors.red, width: 2, type: 'dashed' },
        itemStyle: { color: chartColors.red, borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(199,92,74,0.08)' },
            { offset: 1, color: 'rgba(199,92,74,0.01)' },
          ]),
        },
        data: trend.value.failed,
        animationDuration: 1200,
        animationDelay: 200,
      },
    ],
  })
}

function renderPlatformChart() {
  if (!platformChartRef.value || !platforms.value.length) return
  if (!platformChartInstance) {
    platformChartInstance = echarts.init(platformChartRef.value)
  }
  const total = platforms.value.reduce((s, p) => s + p.value, 0)
  const colors = [chartColors.copper, chartColors.red, chartColors.green, chartColors.blue]

  platformChartInstance.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: '#FFFDF9',
      borderColor: chartColors.border,
      borderWidth: 1,
      textStyle: { color: '#2D2A26', fontFamily: 'DM Sans', fontSize: 12 },
      formatter: '{b}: {c} 个任务 ({d}%)',
    },
    legend: {
      orient: 'vertical', right: 12, top: 'center',
      itemWidth: 10, itemHeight: 10, itemGap: 14,
      textStyle: { color: '#6B6560', fontSize: 12, fontFamily: 'DM Sans' },
      formatter: (name: string) => {
        const item = platforms.value.find(p => p.name === name)
        return `${name}  ${item?.value || 0}`
      },
    },
    series: [{
      type: 'pie',
      radius: ['48%', '72%'],
      center: ['35%', '52%'],
      padAngle: 3,
      itemStyle: { borderRadius: 6 },
      label: {
        show: true, position: 'center',
        formatter: `{total|${total}}\n{label|活跃任务}`,
        rich: {
          total: { fontSize: 26, fontWeight: 600, fontFamily: 'JetBrains Mono', color: '#2D2A26', lineHeight: 34 },
          label: { fontSize: 11, color: '#A39E98', fontFamily: 'DM Sans', lineHeight: 18 },
        },
      },
      emphasis: {
        itemStyle: { shadowBlur: 12, shadowColor: 'rgba(0,0,0,0.08)' },
      },
      data: platforms.value.map((p, i) => ({
        value: p.value,
        name: p.name,
        itemStyle: { color: colors[i % colors.length] },
      })),
      animationType: 'expansion',
      animationDuration: 1000,
    }],
  })
}

// ── Resize ──
function handleResize() {
  trendChartInstance?.resize()
  platformChartInstance?.resize()
}

// ── Fetch data ──
async function loadData() {
  const [s, t, p, r, h, td] = await Promise.all([
    dashboardApi.getStats().catch(() => null),
    dashboardApi.getTrend().catch(() => null),
    dashboardApi.getPlatform().catch(() => []),
    dashboardApi.getRecentRuns().catch(() => []),
    dashboardApi.getHealth().catch(() => null),
    dashboardApi.getTodos().catch(() => []),
  ])

  if (s) {
    stats.value = s
    animateCountUp('active_tasks', s.active_tasks)
    animateCountUp('today_success', s.today_success)
    animateCountUp('success_rate_7d', s.success_rate_7d, true)
    animateCountUp('alert_count', s.alert_count)
  }
  if (t) trend.value = t
  platforms.value = p
  recentRuns.value = r
  if (h) health.value = h
  todos.value = td

  await nextTick()
  renderTrendChart()
  renderPlatformChart()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChartInstance?.dispose()
  platformChartInstance?.dispose()
})
</script>

<style scoped>
/* ── Stats Row ── */
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 22px 24px;
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  overflow: hidden;
  opacity: 0;
  transform: translateY(16px);
  animation: fadeUp 0.55s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: var(--accent-copper-light);
}

.stat-top-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.bar-copper { background: linear-gradient(90deg, var(--accent-copper), var(--accent-copper-light)); }
.bar-green { background: linear-gradient(90deg, var(--accent-green), var(--accent-green-light)); }
.bar-blue { background: linear-gradient(90deg, var(--accent-blue), var(--accent-blue-light)); }
.bar-red { background: linear-gradient(90deg, var(--accent-red), var(--accent-red-light)); }

.stat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.stat-label {
  font-size: 12.5px;
  color: var(--text-tertiary);
  font-weight: 500;
}

.stat-icon-wrap {
  width: 34px; height: 34px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.icon-copper { background: var(--accent-copper-bg); color: var(--accent-copper); }
.icon-green { background: var(--accent-green-bg); color: var(--accent-green); }
.icon-blue { background: var(--accent-blue-bg); color: var(--accent-blue); }
.icon-red { background: var(--accent-red-bg); color: var(--accent-red); }
.icon-amber { background: var(--accent-amber-bg); color: var(--accent-amber); }

.stat-value {
  font-family: var(--font-mono);
  font-size: 30px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -1px;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.stat-trend {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 4px;
}
.trend-up { color: var(--accent-green); background: var(--accent-green-bg); }
.trend-down { color: var(--accent-red); background: var(--accent-red-bg); }

/* ── Charts ── */
.charts-row {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(320px, 1fr);
  gap: 18px;
  margin-bottom: 24px;
}

.card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
  opacity: 0;
  transform: translateY(16px);
  animation: fadeUp 0.55s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  transition: box-shadow 0.3s, border-color 0.3s;
}
.card:hover { box-shadow: var(--shadow-md); border-color: var(--border); }

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px 0;
}

.card-title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-actions { display: flex; gap: 4px; }

.card-action-btn {
  padding: 5px 11px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 500;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.2s;
  font-family: var(--font-body);
}
.card-action-btn:hover { background: var(--bg-subtle); color: var(--text-secondary); }
.card-action-btn.active {
  background: var(--accent-copper-bg);
  color: var(--accent-copper);
  border-color: var(--accent-copper-light);
}

.chart-container {
  padding: 12px 16px 16px;
  height: 260px;
}

/* ── Table ── */
.table-card { margin-bottom: 24px; }

.table-wrap { padding: 0 6px 6px; overflow-x: auto; }

table { width: 100%; border-collapse: collapse; }

thead th {
  text-align: left;
  padding: 12px 16px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  border-bottom: 1px solid var(--border-light);
  white-space: nowrap;
}

tbody tr { transition: background 0.15s; cursor: pointer; }
tbody tr:hover { background: var(--bg-hover); }

tbody td {
  padding: 13px 16px;
  font-size: 13px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-light);
  white-space: nowrap;
}
tbody tr:last-child td { border-bottom: none; }

.cell-task { display: flex; align-items: center; gap: 10px; }

.task-icon-sm {
  width: 30px; height: 30px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.task-name { font-weight: 500; color: var(--text-primary); }
.task-sub { font-size: 11.5px; color: var(--text-tertiary); }

.platform-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  font-size: 11.5px;
  font-weight: 500;
  background: var(--bg-subtle);
  color: var(--text-secondary);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  font-size: 11.5px;
  font-weight: 550;
}
.status-success { background: var(--accent-green-bg); color: var(--accent-green); }
.status-failed { background: var(--accent-red-bg); color: var(--accent-red); }
.status-running { background: var(--accent-blue-bg); color: var(--accent-blue); }
.status-pending { background: var(--accent-amber-bg); color: var(--accent-amber); }

.status-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.status-running .status-dot { animation: pulseDot 1.5s ease-in-out infinite; }

.cell-mono {
  font-family: var(--font-mono);
  font-size: 12.5px;
  color: var(--text-secondary);
}
.cell-time { font-size: 12.5px; color: var(--text-tertiary); }

/* ── Bottom Row ── */
.bottom-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 18px;
}

.health-list {
  padding: 16px 22px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.health-item {
  display: flex;
  align-items: center;
  gap: 14px;
}

.health-bar-wrap {
  flex: 1;
  height: 8px;
  background: var(--bg-subtle);
  border-radius: var(--radius-pill);
  overflow: hidden;
}

.health-bar {
  height: 100%;
  border-radius: var(--radius-pill);
  transition: width 1.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.health-label {
  font-size: 12.5px;
  color: var(--text-secondary);
  width: 72px;
  flex-shrink: 0;
}

.health-value {
  font-family: var(--font-mono);
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-primary);
  width: 36px;
  text-align: right;
  flex-shrink: 0;
}

.platform-status-section {
  margin-top: 8px;
  padding-top: 14px;
  border-top: 1px solid var(--border-light);
}

.section-label {
  font-size: 12px;
  color: var(--text-tertiary);
  font-weight: 500;
  display: block;
  margin-bottom: 10px;
}

.platform-tags { display: flex; gap: 10px; flex-wrap: wrap; }

.platform-status-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  font-size: 11.5px;
  font-weight: 500;
}
.ps-healthy { background: var(--accent-green-bg); color: var(--accent-green); }
.ps-warning { background: var(--accent-amber-bg); color: var(--accent-amber); }
.ps-invalid { background: var(--accent-red-bg); color: var(--accent-red); }
.ps-dot {
  width: 6px; height: 6px;
  background: currentColor;
  border-radius: 50%;
}

/* ── Todo ── */
.todo-list {
  padding: 12px 22px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  transition: background 0.15s;
  cursor: pointer;
}
.todo-item:hover { background: var(--bg-hover); }

.todo-priority {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.priority-high { background: var(--accent-red); }
.priority-medium { background: var(--accent-amber); }
.priority-low { background: var(--accent-green); }

.todo-text {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
}

.todo-tag {
  font-size: 10.5px;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  font-weight: 500;
}
.tag-urgent { background: var(--accent-red-bg); color: var(--accent-red); }
.tag-warn { background: var(--accent-amber-bg); color: var(--accent-amber); }
.tag-info { background: var(--accent-blue-bg); color: var(--accent-blue); }

.todo-time {
  font-size: 11.5px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

/* ── Responsive ── */
@media (max-width: 1200px) {
  .stats-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .charts-row { grid-template-columns: 1fr; }
  .bottom-row { grid-template-columns: 1fr; }
}

@media (max-width: 760px) {
  .stats-row { grid-template-columns: 1fr; }
}
</style>
