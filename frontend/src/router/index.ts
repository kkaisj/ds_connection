/**
 * 路由配置
 * 所有业务页面挂载在 AppLayout 布局下，共享侧边导航和顶栏。
 */

import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/pages/Dashboard.vue'),
          meta: { title: '运营看板' },
        },
        {
          path: 'marketplace',
          name: 'marketplace',
          component: () => import('@/pages/Marketplace.vue'),
          meta: { title: '连接市场' },
        },
        {
          path: 'app-management',
          name: 'app-management',
          component: () => import('@/pages/AppManagement.vue'),
          meta: { title: '应用管理' },
        },
        {
          path: 'release-management',
          name: 'release-management',
          component: () => import('@/pages/ReleaseManagement.vue'),
          meta: { title: '发版管理' },
        },
        {
          path: 'adapter-workbench',
          name: 'adapter-workbench',
          component: () => import('@/pages/AdapterWorkbench.vue'),
          meta: { title: '适配器工作台' },
        },
        {
          path: 'my-instructions',
          name: 'my-instructions',
          component: () => import('@/pages/AdapterWorkbench.vue'),
          meta: { title: '适配器工作台' },
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('@/pages/Tasks.vue'),
          meta: { title: '连接任务' },
        },
        {
          path: 'accounts',
          name: 'accounts',
          component: () => import('@/pages/Accounts.vue'),
          meta: { title: '账号管理' },
        },
        {
          path: 'executions',
          name: 'executions',
          component: () => import('@/pages/Executions.vue'),
          meta: { title: '执行记录' },
        },
        {
          path: 'storages',
          name: 'storages',
          component: () => import('@/pages/Storages.vue'),
          meta: { title: '存储管理' },
        },
        {
          path: 'notifications',
          name: 'notifications',
          component: () => import('@/pages/Notifications.vue'),
          meta: { title: '消息通知' },
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/pages/Settings.vue'),
          meta: { title: '系统设置' },
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const title = (to.meta.title as string) || 'DC 数据连接器'
  document.title = `${title} - DC`
})

export default router
