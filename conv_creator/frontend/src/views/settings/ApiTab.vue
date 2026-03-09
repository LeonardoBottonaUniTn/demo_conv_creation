<template>
  <section class="panel stack">
    <div class="alert-stack">
      <p v-if="error" class="alert error">{{ error }}</p>
      <p v-if="success" class="alert success">{{ success }}</p>
    </div>

    <form class="settings-form" @submit.prevent="$emit('save')">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Credentials</p>
          <h3>Groq API key</h3>
        </div>
        <span class="chip safe">{{ hasApiKey ? 'Stored securely' : 'Pending setup' }}</span>
      </div>
      <p class="muted small">
        Keys are encrypted in the backend. Enter a new key below to rotate credentials or leave
        blank to keep the current one.
      </p>
      <label class="field-label" for="apiKey">API key</label>
      <input
        id="apiKey"
        :value="apiKey"
        type="password"
        autocomplete="off"
        :placeholder="
          hasApiKey ? 'Key already configured – enter a new one to replace' : 'Enter your API key'
        "
        :disabled="loading"
        @input="emit('update:apiKey', ($event.target as HTMLInputElement).value)"
      />
      <p class="helper">
        {{ hasApiKey ? 'A key is already saved.' : 'Required to run LLM calls.' }}
      </p>

      <div class="panel-head">
        <div>
          <p class="eyebrow">Model preference</p>
          <h3>Primary LLM</h3>
        </div>
        <span class="chip neutral">{{ availableModels.length }} options</span>
      </div>
      <label class="field-label" for="model">Preferred model</label>
      <select
        id="model"
        :value="model"
        :disabled="loading || availableModels.length === 0"
        @change="emit('update:model', ($event.target as HTMLSelectElement).value)"
      >
        <option value="" disabled>Select a model</option>
        <option v-for="m in availableModels" :key="m" :value="m">
          {{ m }}
        </option>
      </select>
      <p v-if="availableModels.length === 0" class="inline-error">
        No models available. Contact your administrator.
      </p>
      <div v-else class="model-chips">
        <button
          v-for="option in quickModelOptions"
          :key="option"
          type="button"
          class="chip-button"
          @click="$emit('update:model', option)"
        >
          {{ option }}
        </button>
      </div>

      <div class="actions-bar">
        <button type="button" class="btn ghost" :disabled="loading" @click="$emit('reset')">
          Cancel
        </button>
        <button class="btn primary" type="submit" :disabled="loading">
          <span v-if="!loading">Save Settings</span>
          <span v-else>Saving…</span>
        </button>
      </div>
    </form>

    <div class="status-panel">
      <ul>
        <li>
          <span class="badge" :class="hasApiKey ? 'success' : 'warning'">
            {{ hasApiKey ? 'Active' : 'Missing' }}
          </span>
          API key {{ hasApiKey ? 'on file' : 'not configured' }}
        </li>
        <li>
          <span class="badge neutral">Model</span>
          {{ model || 'No model selected' }}
        </li>
        <li>
          <span class="badge neutral">Last sync</span>
          {{ lastSynced || 'Not synced yet' }}
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  apiKey: string
  hasApiKey: boolean
  model: string
  availableModels: string[]
  quickModelOptions: string[]
  loading: boolean
  error: string
  success: string
  lastSynced: string
}>()

const emit = defineEmits<{
  (e: 'update:apiKey', value: string): void
  (e: 'update:model', value: string): void
  (e: 'reset'): void
  (e: 'save'): void
}>()
</script>
