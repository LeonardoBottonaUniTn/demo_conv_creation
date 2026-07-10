<template>
  <section class="panel stack">
    <h3>About this workspace</h3>
    <p class="muted">
      Conv Creator keeps your experiment settings synced across every device. API credentials stay
      on the server and never ship to the browser after saving.
    </p>
    <div class="about-grid">
      <article>
        <h4>Infrastructure</h4>
        <p>Built with Vue 3, Vite, and OpenAI/Groq-compatible LLM backends.</p>
      </article>
      <article>
        <h4>Support</h4>
        <p>Reach us at support@example.com for enterprise plans or uptime questions.</p>
      </article>
      <article>
        <h4>Version</h4>
        <p>Frontend v1.4.0 · Backend v1.3.2 · Last deploy {{ lastSynced || 'N/A' }}</p>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{ lastSynced: string }>()
</script>
