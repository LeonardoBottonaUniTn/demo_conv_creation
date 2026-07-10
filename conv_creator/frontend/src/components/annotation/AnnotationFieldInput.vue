<script setup lang="ts">
import MultiSelect from 'primevue/multiselect'
import Dropdown from 'primevue/dropdown'
import type { AnnotationFieldDefinition } from '../../types/annotation'

const props = defineProps<{
  field: AnnotationFieldDefinition
  modelValue: unknown
}>()

const emit = defineEmits<{
  'update:modelValue': [value: unknown]
}>()

const ratingOptions = [
  { label: '—', value: null },
  { label: '1 — Poor', value: 1 },
  { label: '2', value: 2 },
  { label: '3 — Average', value: 3 },
  { label: '4', value: 4 },
  { label: '5 — Excellent', value: 5 },
]

function labelOptions(options: string[] | undefined) {
  return (options ?? []).map((option) => ({ label: option, value: option }))
}
</script>

<template>
  <div class="field">
    <label>{{ field.label }}</label>

    <MultiSelect
      v-if="field.type === 'labels'"
      :model-value="(modelValue as string[]) ?? []"
      :options="labelOptions(field.options)"
      option-label="label"
      option-value="value"
      :placeholder="`Select ${field.label.toLowerCase()}`"
      display="chip"
      class="annotation-multiselect"
      @update:model-value="emit('update:modelValue', $event ?? [])"
    />

    <Dropdown
      v-else-if="field.type === 'select'"
      :model-value="modelValue"
      :options="labelOptions(field.options)"
      option-label="label"
      option-value="value"
      :placeholder="field.placeholder || `Select ${field.label.toLowerCase()}`"
      class="annotation-dropdown"
      @update:model-value="emit('update:modelValue', $event)"
    />

    <Dropdown
      v-else-if="field.type === 'rating'"
      :model-value="modelValue"
      :options="ratingOptions"
      option-label="label"
      option-value="value"
      :placeholder="field.placeholder || `Rate ${field.label.toLowerCase()}`"
      class="annotation-dropdown"
      @update:model-value="emit('update:modelValue', $event)"
    />

    <input
      v-else-if="field.type === 'text'"
      :value="(modelValue as string) ?? ''"
      type="text"
      :placeholder="field.placeholder || field.label"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />

    <input
      v-else-if="field.type === 'number'"
      :value="modelValue === null || modelValue === undefined ? '' : String(modelValue)"
      type="number"
      :placeholder="field.placeholder || field.label"
      @input="
        emit(
          'update:modelValue',
          ($event.target as HTMLInputElement).value === ''
            ? null
            : Number(($event.target as HTMLInputElement).value),
        )
      "
    />

    <textarea
      v-else
      :value="(modelValue as string) ?? ''"
      rows="5"
      :placeholder="field.placeholder || field.label"
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
    ></textarea>
  </div>
</template>

<style scoped>
.field {
  margin-bottom: 1rem;
}

.field label {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--muted);
  margin-bottom: 0.35rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.field input,
.field textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #dee2e6;
  border-radius: 10px;
  padding: 0.65rem 0.75rem;
  font-family: inherit;
  font-size: 0.9rem;
  resize: vertical;
}

.field input:focus,
.field textarea:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.15);
}

:deep(.annotation-multiselect),
:deep(.annotation-dropdown) {
  width: 100%;
}
</style>
