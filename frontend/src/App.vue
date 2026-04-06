<!--
  根组件
  配置 Naive UI 主题覆盖（奶油暖色调），注入全局 Message / Dialog Provider。
-->
<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <router-view />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { NConfigProvider, NMessageProvider, NDialogProvider, type GlobalThemeOverrides } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#C8956C',
    primaryColorHover: '#B88560',
    primaryColorPressed: '#A87A55',
    bodyColor: '#FDFBF7',
    cardColor: '#FFFFFF',
    borderColor: '#E8E3DC',
    textColorBase: '#2D2A26',
    textColor1: '#2D2A26',
    textColor2: '#6B6560',
    textColor3: '#A39E98',
    borderRadius: '8px',
    fontFamily: "'DM Sans', -apple-system, sans-serif",
  },
}
</script>
