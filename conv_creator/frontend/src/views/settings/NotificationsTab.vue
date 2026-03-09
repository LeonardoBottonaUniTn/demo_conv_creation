<template>
  <section class="panel stack">
    <h3>Alert preferences</h3>
    <div class="toggle-list">
      <label class="toggle-item">
        <input
          type="checkbox"
          :checked="productUpdates"
          @change="$emit('update:productUpdates', ($event.target as HTMLInputElement).checked)"
        />
        <span class="toggle-control"></span>
        <div>
          <strong>Product updates</strong>
          <p>News about new workflows and templates.</p>
        </div>
      </label>

      <label class="toggle-item">
        <input
          type="checkbox"
          :checked="securityAlerts"
          @change="$emit('update:securityAlerts', ($event.target as HTMLInputElement).checked)"
        />
        <span class="toggle-control"></span>
        <div>
          <strong>Security alerts</strong>
          <p>Be notified about suspicious sign-in attempts.</p>
        </div>
      </label>

      <label class="toggle-item">
        <input
          type="checkbox"
          :checked="weeklyDigest"
          @change="$emit('update:weeklyDigest', ($event.target as HTMLInputElement).checked)"
        />
        <span class="toggle-control"></span>
        <div>
          <strong>Weekly digest</strong>
          <p>Summary of activity delivered every Monday.</p>
        </div>
      </label>

      <label class="toggle-item">
        <input
          type="checkbox"
          :checked="smsAlerts"
          @change="$emit('update:smsAlerts', ($event.target as HTMLInputElement).checked)"
        />
        <span class="toggle-control"></span>
        <div>
          <strong>SMS alerts</strong>
          <p>Critical updates sent via text message.</p>
        </div>
      </label>
    </div>
    <div class="actions-bar">
      <button
        type="button"
        class="btn ghost"
        :disabled="notificationSaving"
        @click="$emit('reset')"
      >
        Reset
      </button>
      <button
        type="button"
        class="btn primary"
        :disabled="notificationSaving"
        @click="$emit('save')"
      >
        <span v-if="!notificationSaving">Save Preferences</span>
        <span v-else>Saving…</span>
      </button>
    </div>
    <p v-if="notificationMessage" class="inline-success">{{ notificationMessage }}</p>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  productUpdates: boolean
  securityAlerts: boolean
  weeklyDigest: boolean
  smsAlerts: boolean
  notificationSaving: boolean
  notificationMessage: string
}>()

defineEmits<{
  (e: 'update:productUpdates', value: boolean): void
  (e: 'update:securityAlerts', value: boolean): void
  (e: 'update:weeklyDigest', value: boolean): void
  (e: 'update:smsAlerts', value: boolean): void
  (e: 'reset'): void
  (e: 'save'): void
}>()
</script>
