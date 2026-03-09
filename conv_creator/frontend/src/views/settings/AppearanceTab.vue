<template>
  <section class="panel stack">
    <h3>Theme &amp; density</h3>
    <div class="appearance-grid">
      <div>
        <label class="field-label" for="theme">Theme</label>
        <select
          id="theme"
          :value="theme"
          @change="$emit('update:theme', ($event.target as HTMLSelectElement).value)"
        >
          <option value="system">Match system</option>
          <option value="light">Light mode</option>
          <option value="dark">Dark mode</option>
        </select>
      </div>
      <div>
        <label class="field-label" for="density">Interface density</label>
        <select
          id="density"
          :value="density"
          @change="$emit('update:density', ($event.target as HTMLSelectElement).value)"
        >
          <option value="cozy">Cozy</option>
          <option value="compact">Compact</option>
          <option value="spacious">Spacious</option>
        </select>
      </div>
    </div>

    <h3>Accent color</h3>
    <div class="accent-row">
      <button
        v-for="accentOption in accentOptions"
        :key="accentOption.key"
        type="button"
        class="accent-chip"
        :class="{ active: accent === accentOption.key }"
        :style="accentStyles[accentOption.key]"
        @click="$emit('update:accent', accentOption.key)"
      >
        {{ accentOption.label }}
      </button>
    </div>

    <div class="actions-bar">
      <button type="button" class="btn ghost" :disabled="appearanceSaving" @click="$emit('reset')">
        Reset
      </button>
      <button type="button" class="btn primary" :disabled="appearanceSaving" @click="$emit('save')">
        <span v-if="!appearanceSaving">Apply Theme</span>
        <span v-else>Applying…</span>
      </button>
    </div>
    <p v-if="appearanceMessage" class="inline-success">{{ appearanceMessage }}</p>
  </section>
</template>

<script setup lang="ts">
import type { AccentKey, AccentOption, AccentStyles } from './types'

defineProps<{
  theme: string
  density: string
  accent: AccentKey
  accentOptions: AccentOption[]
  accentStyles: AccentStyles
  appearanceSaving: boolean
  appearanceMessage: string
}>()

defineEmits<{
  (e: 'update:theme', value: string): void
  (e: 'update:density', value: string): void
  (e: 'update:accent', value: string): void
  (e: 'reset'): void
  (e: 'save'): void
}>()
</script>
