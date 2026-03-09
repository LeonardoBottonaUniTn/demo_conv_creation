<template>
  <section class="panel profile-panel">
    <div class="avatar-large">{{ userInitial }}</div>
    <div class="profile-form">
      <div class="profile-head">
        <h2>{{ displayName }}</h2>
        <p class="muted small">Manage how your workspace sees you.</p>
      </div>

      <label class="field-label" for="fullName">Full name</label>
      <input
        id="fullName"
        :value="profileName"
        type="text"
        placeholder="LLM User"
        @input="onNameInput"
      />

      <label class="field-label" for="profileEmail">Email address</label>
      <input id="profileEmail" :value="profileEmail" type="email" readonly />

      <div class="actions-bar">
        <button type="button" class="btn ghost" :disabled="profileSaving" @click="$emit('reset')">
          Cancel
        </button>
        <button type="button" class="btn primary" :disabled="profileSaving" @click="$emit('save')">
          <span v-if="!profileSaving">Save Changes</span>
          <span v-else>Saving…</span>
        </button>
      </div>
      <p v-if="profileMessage" class="inline-success">{{ profileMessage }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  userInitial: string
  displayName: string
  profileName: string
  profileEmail: string
  profileSaving: boolean
  profileMessage: string
}>()

const emit = defineEmits<{
  (e: 'update:profileName', value: string): void
  (e: 'touched'): void
  (e: 'reset'): void
  (e: 'save'): void
}>()

function onNameInput(event: Event) {
  const value = (event.target as HTMLInputElement).value
  emit('update:profileName', value)
  emit('touched')
}
</script>
