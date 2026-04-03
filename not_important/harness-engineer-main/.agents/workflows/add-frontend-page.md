---
description: 新增一个前端页面的标准流程
---

# 新增前端页面

## 步骤

### 1. 阅读相关文档

- 阅读 `uav-frontend/AGENTS.md` 了解前端架构
- 阅读 `docs/conventions/frontend-coding-style.md` 了解编码规范
- 阅读 `docs/architecture/frontend-layers.md` 了解分层规则

### 2. 定义类型（如需要）

- 路径：`src/types/index.ts` 或新建 `src/types/xxx.ts`
- 定义接口数据类型，与后端 VO 对应

### 3. 创建 API 封装

- 路径：`src/api/xxx.ts`
- 导入 `request` 从 `@/api/request`
- 定义函数：`getXxx`, `createXxx`, `updateXxx`, `deleteXxx`
- 所有函数返回 `Promise<T>`

### 4. 创建 Store（如需要）

- 路径：`src/store/xxx.ts`
- 使用 `defineStore('xxx', () => { ... })`
- Actions 调用 `api/` 层方法

### 5. 创建页面组件

- 路径：`src/views/XxxView.vue` 或 `src/views/system/XxxManageView.vue`
- 使用 `<script setup lang="ts">`
- 通过 `api/` 层获取数据，禁止直接使用 axios
- 使用 Element Plus 组件 + Tailwind CSS

### 6. 注册路由

- 路径：`src/router/index.ts`
- 在 `MainLayout` children 中添加路由
- 使用懒加载：`component: () => import('@/views/xxx.vue')`
- 设置 `name` 属性

### 7. 更新侧边栏（如需要）

- 路径：`src/components/layout/Sidebar.vue`
- 添加菜单项

### 8. 验证

// turbo
```bash
cd uav-frontend && npm run lint && npm run check
```

// turbo
```bash
cd uav-frontend && npm run build
```
