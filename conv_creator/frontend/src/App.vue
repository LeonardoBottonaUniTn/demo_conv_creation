<script setup lang="ts">
// The App component now only handles routing
// All the discussion logic has been moved to DiscussionPage.vue
</script>

<template>
  <div id="app">
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

#app {
  height: 100vh;
  width: 100vw;
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
</style>
