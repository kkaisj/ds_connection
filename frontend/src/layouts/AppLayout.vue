<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-icon">DC</div>
        <div class="brand-text">
          <span class="brand-name">数据连接器</span>
          <span class="brand-sub">DATA CONNECTION</span>
        </div>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-label">概览</div>
        <router-link
          v-for="item in overviewNav"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
        >
          <component :is="item.icon" class="nav-icon-component" />
          <span>{{ item.label }}</span>
          <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
        </router-link>

        <div class="nav-label">业务</div>
        <router-link
          v-for="item in businessNav"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
        >
          <component :is="item.icon" class="nav-icon-component" />
          <span>{{ item.label }}</span>
          <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
        </router-link>

        <div class="nav-label">数据</div>
        <router-link
          v-for="item in dataNav"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
        >
          <component :is="item.icon" class="nav-icon-component" />
          <span>{{ item.label }}</span>
        </router-link>

        <div class="nav-label">系统</div>
        <router-link
          v-for="item in systemNav"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
        >
          <component :is="item.icon" class="nav-icon-component" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="user-card">
          <div class="user-avatar">困</div>
          <div class="user-info">
            <span class="user-name">困困</span>
            <span class="user-role">管理员</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main -->
    <main class="main-content">
      <header class="header">
        <div class="header-left">
          <h1 class="page-title">{{ route.meta.title || '运营看板' }}</h1>
          <span class="header-date">{{ todayStr }}</span>
        </div>
        <div class="header-right">
          <n-button secondary size="small">导出报告</n-button>
          <n-button type="primary" size="small" class="btn-copper">+ 新建任务</n-button>
        </div>
      </header>

      <div class="page-container">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue'
import { useRoute } from 'vue-router'
import { NButton } from 'naive-ui'
import {
  GridOutline,
  GlobeOutline,
  BarChartOutline,
  PeopleOutline,
  DocumentTextOutline,
  ServerOutline,
  NotificationsOutline,
  SettingsOutline,
} from '@vicons/ionicons5'

const route = useRoute()

const today = new Date()
const todayStr = `${today.getFullYear()} 年 ${today.getMonth() + 1} 月 ${today.getDate()} 日`

const iconWrap = (icon: object) => () => h('div', { class: 'nav-icon' }, [h(icon as any)])

const overviewNav = [
  { path: '/', label: '看板', icon: iconWrap(GridOutline) },
]

const businessNav = [
  { path: '/marketplace', label: '连接市场', icon: iconWrap(GlobeOutline) },
  { path: '/tasks', label: '连接任务', icon: iconWrap(BarChartOutline), badge: 3 },
  { path: '/accounts', label: '账号管理', icon: iconWrap(PeopleOutline) },
]

const dataNav = [
  { path: '/executions', label: '执行记录', icon: iconWrap(DocumentTextOutline) },
  { path: '/storages', label: '存储管理', icon: iconWrap(ServerOutline) },
  { path: '/notifications', label: '消息通知', icon: iconWrap(NotificationsOutline) },
]

const systemNav = [
  { path: '/settings', label: '系统设置', icon: iconWrap(SettingsOutline) },
]
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

/* ── Sidebar ── */
.sidebar {
  width: var(--sidebar-w);
  background: var(--bg-card);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
  animation: slideInLeft 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.sidebar-brand {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--accent-copper), #A87A55);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.brand-text { display: flex; flex-direction: column; }
.brand-name {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.2;
  letter-spacing: -0.3px;
}
.brand-sub {
  font-size: 10px;
  color: var(--text-tertiary);
  letter-spacing: 1.2px;
}

.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.nav-label {
  font-size: 10.5px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 1.2px;
  padding: 16px 12px 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 13.5px;
  font-weight: 450;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  text-decoration: none;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-copper-bg);
  color: var(--accent-copper);
  font-weight: 550;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: var(--accent-copper);
  border-radius: 0 3px 3px 0;
}

.nav-icon {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.65;
  flex-shrink: 0;
}

.nav-item.active .nav-icon { opacity: 1; }

:deep(.nav-icon-component) {
  display: flex;
}

.nav-badge {
  margin-left: auto;
  background: var(--accent-red);
  color: white;
  font-size: 10.5px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  font-family: var(--font-mono);
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-light);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.2s;
}
.user-card:hover { background: var(--bg-hover); }

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-green), var(--accent-blue));
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: 600;
}

.user-info { display: flex; flex-direction: column; }
.user-name { font-size: 12.5px; font-weight: 550; color: var(--text-primary); }
.user-role { font-size: 11px; color: var(--text-tertiary); }

/* ── Main ── */
.main-content {
  flex: 1;
  margin-left: var(--sidebar-w);
  min-height: 100vh;
  width: calc(100vw - var(--sidebar-w));
}

.header {
  height: var(--header-h);
  padding: 0 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-light);
  background: rgba(253,251,247,0.85);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 50;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.header-date {
  font-size: 12.5px;
  color: var(--text-tertiary);
  font-weight: 400;
  padding: 4px 12px;
  background: var(--bg-subtle);
  border-radius: var(--radius-pill);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-copper {
  background: linear-gradient(135deg, var(--accent-copper), #B88560) !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(200,149,108,0.3);
}
.btn-copper:hover {
  box-shadow: 0 4px 16px rgba(200,149,108,0.4) !important;
  transform: translateY(-1px);
}

.page-container {
  padding: 28px 32px 48px;
  width: 100%;
  max-width: none;
}
</style>
