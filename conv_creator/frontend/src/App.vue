<script setup lang="ts">
import HeaderBar from './components/HeaderBar.vue'
</script>

<template>
  <div id="app">
    <HeaderBar />
    <router-view />
  </div>
</template>

<style>
@import './styles/theme.css';
html,
body {
  height: 100%;
  margin: 0;
  padding: 0;
}

body {
  min-height: 100vh;
  font-family:
    'Space Grotesk',
    'Inter',
    'Segoe UI',
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    sans-serif;
  background: linear-gradient(135deg, var(--bg-100) 0%, var(--bg-200) 100%);
  background-attachment: fixed;
  color: var(--text-900);
}

#app {
  min-height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
}

/* Allow scrolling for specific route components */
.home-page {
  overflow-y: auto !important;
}

.files-page {
  overflow-y: auto !important;
  height: auto !important;
  min-height: 100vh !important;
}

/* Ensure discussion page doesn't overflow */
.discussion-page {
  overflow: hidden !important;
}

/* Lock the whole app to the viewport height on the discussion route so the
   only things that can scroll are the inner panels (e.g. the chat message list). */
#app:has(.discussion-page) {
  height: 100vh;
  min-height: 0;
  overflow: hidden;
}

.annotation-page {
  overflow: hidden !important;
  flex: 1;
  min-height: 0;
}
</style>
