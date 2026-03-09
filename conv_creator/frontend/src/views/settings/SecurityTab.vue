<template>
  <section class="panel stack">
    <h3>Security status</h3>
    <ul class="status-grid">
      <li>
        <span class="badge success">Enabled</span>
        Multi-factor authentication active on your account.
      </li>
      <li>
        <span class="badge neutral">Devices</span>
        {{ securityState.devices }} trusted devices linked.
      </li>
      <li>
        <span class="badge neutral">Password</span>
        Updated {{ securityState.passwordUpdated }}.
      </li>
    </ul>

    <section class="panel danger-panel">
      <div>
        <p class="eyebrow danger">Danger zone</p>
        <h3>Delete account</h3>
        <p class="muted small">
          Irreversible action. Contact an administrator to proceed with a full removal.
        </p>
      </div>
      <button class="btn danger" type="button" disabled title="Contact your administrator">
        Delete Account
      </button>
    </section>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  securityState: {
    devices: number
    passwordUpdated: string
  }
}>()
</script>
