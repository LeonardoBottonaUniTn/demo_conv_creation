<script setup lang="ts">
import { ref, watch } from 'vue'
import type { AnnotationFieldDefinition, AnnotationSchema } from '../../types/annotation'
import { cloneSchema, fieldDefaultValue, slugifyFieldId } from '../../types/annotation'

const props = defineProps<{
  modelValue: AnnotationSchema
  saving?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [schema: AnnotationSchema]
  save: [schema: AnnotationSchema]
  close: []
}>()

const localSchema = ref<AnnotationSchema>(cloneSchema(props.modelValue))
const activeTab = ref<'message' | 'conversation'>('message')

watch(
  () => props.modelValue,
  (value) => {
    localSchema.value = cloneSchema(value)
  },
)

const fieldTypes = [
  { value: 'labels', label: 'Labels (multi-select)' },
  { value: 'text', label: 'Short text' },
  { value: 'textarea', label: 'Long text' },
  { value: 'rating', label: 'Rating (1–5)' },
  { value: 'select', label: 'Single choice' },
  { value: 'number', label: 'Number' },
]

function fieldsForScope(scope: 'message' | 'conversation') {
  return scope === 'message' ? localSchema.value.messageFields : localSchema.value.conversationFields
}

function existingIds(excludeIndex?: number, scope: 'message' | 'conversation' = 'message') {
  const fields = fieldsForScope(scope)
  return new Set(
    fields
      .filter((_field: AnnotationFieldDefinition, index: number) => index !== excludeIndex)
      .map((field: AnnotationFieldDefinition) => field.id),
  )
}

function addField(scope: 'message' | 'conversation') {
  const ids = existingIds(undefined, scope)
  const id = slugifyFieldId('new_field', ids)
  const field: AnnotationFieldDefinition = {
    id,
    label: 'New field',
    type: 'text',
    options: scope === 'message' ? [] : undefined,
  }
  if (scope === 'message') {
    localSchema.value.messageFields.push(field)
  } else {
    localSchema.value.conversationFields.push(field)
  }
}

function removeField(scope: 'message' | 'conversation', index: number) {
  if (scope === 'message') {
    localSchema.value.messageFields.splice(index, 1)
  } else {
    localSchema.value.conversationFields.splice(index, 1)
  }
}

function moveField(scope: 'message' | 'conversation', index: number, direction: -1 | 1) {
  const fields = fieldsForScope(scope)
  const target = index + direction
  if (target < 0 || target >= fields.length) return
  const [item] = fields.splice(index, 1)
  fields.splice(target, 0, item)
}

function onLabelChange(scope: 'message' | 'conversation', index: number, label: string) {
  const fields = fieldsForScope(scope)
  const field = fields[index]
  field.label = label
  if (field.id.startsWith('new_field') || field.id === slugifyFieldId('new_field', new Set())) {
    field.id = slugifyFieldId(label || 'field', existingIds(index, scope))
  }
}

function onTypeChange(scope: 'message' | 'conversation', index: number, type: AnnotationFieldDefinition['type']) {
  const field = fieldsForScope(scope)[index]
  field.type = type
  if (type === 'labels' || type === 'select') {
    field.options = field.options ?? []
  } else {
    delete field.options
  }
}

function addOption(scope: 'message' | 'conversation', fieldIndex: number) {
  const field = fieldsForScope(scope)[fieldIndex]
  if (!field.options) field.options = []
  field.options.push('')
}

function removeOption(scope: 'message' | 'conversation', fieldIndex: number, optionIndex: number) {
  const field = fieldsForScope(scope)[fieldIndex]
  field.options?.splice(optionIndex, 1)
}

function handleSave() {
  const cleaned = cloneSchema(localSchema.value)
  cleaned.messageFields = cleaned.messageFields
    .map((field: AnnotationFieldDefinition) => ({
      ...field,
      label: field.label.trim(),
      id: field.id.trim(),
      options:
        field.type === 'labels' || field.type === 'select'
          ? (field.options ?? []).map((o: string) => o.trim()).filter(Boolean)
          : undefined,
    }))
    .filter((field: AnnotationFieldDefinition) => field.label && field.id)

  cleaned.conversationFields = cleaned.conversationFields
    .map((field: AnnotationFieldDefinition) => ({
      ...field,
      label: field.label.trim(),
      id: field.id.trim(),
      options:
        field.type === 'labels' || field.type === 'select'
          ? (field.options ?? []).map((o: string) => o.trim()).filter(Boolean)
          : undefined,
    }))
    .filter((field: AnnotationFieldDefinition) => field.label && field.id)

  emit('update:modelValue', cleaned)
  emit('save', cleaned)
}
</script>

<template>
  <div class="schema-editor-overlay" @click.self="emit('close')">
    <div class="schema-editor">
      <header class="editor-header">
        <div>
          <h2>Customize labeling fields</h2>
          <p>Add, rename, or remove fields and label options for this labeling template.</p>
        </div>
        <button type="button" class="icon-btn" aria-label="Close" @click="emit('close')">×</button>
      </header>

      <div class="tab-row">
        <button
          type="button"
          class="tab-btn"
          :class="{ active: activeTab === 'message' }"
          @click="activeTab = 'message'"
        >
          Message fields ({{ localSchema.messageFields.length }})
        </button>
        <button
          type="button"
          class="tab-btn"
          :class="{ active: activeTab === 'conversation' }"
          @click="activeTab = 'conversation'"
        >
          Conversation fields ({{ localSchema.conversationFields.length }})
        </button>
      </div>

      <div class="fields-list">
        <article
          v-for="(field, index) in fieldsForScope(activeTab)"
          :key="`${activeTab}-${field.id}-${index}`"
          class="field-card"
        >
          <div class="field-card-toolbar">
            <span class="field-index">#{{ index + 1 }}</span>
            <div class="toolbar-actions">
              <button
                type="button"
                class="tiny-btn"
                :disabled="index === 0"
                @click="moveField(activeTab, index, -1)"
              >
                ↑
              </button>
              <button
                type="button"
                class="tiny-btn"
                :disabled="index === fieldsForScope(activeTab).length - 1"
                @click="moveField(activeTab, index, 1)"
              >
                ↓
              </button>
              <button type="button" class="tiny-btn danger" @click="removeField(activeTab, index)">
                Remove
              </button>
            </div>
          </div>

          <div class="field-grid">
            <label>
              <span>Field label</span>
              <input
                :value="field.label"
                type="text"
                placeholder="e.g. Stance, Quality, Notes"
                @input="onLabelChange(activeTab, index, ($event.target as HTMLInputElement).value)"
              />
            </label>

            <label>
              <span>Field type</span>
              <select
                :value="field.type"
                @change="
                  onTypeChange(
                    activeTab,
                    index,
                    ($event.target as HTMLSelectElement).value as AnnotationFieldDefinition['type'],
                  )
                "
              >
                <option v-for="option in fieldTypes" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>

            <label class="full-width">
              <span>Field id</span>
              <input :value="field.id" type="text" readonly />
            </label>

            <label
              v-if="field.type === 'text' || field.type === 'textarea'"
              class="full-width"
            >
              <span>Placeholder</span>
              <input
                :value="field.placeholder ?? ''"
                type="text"
                placeholder="Optional hint shown in the input"
                @input="field.placeholder = ($event.target as HTMLInputElement).value"
              />
            </label>
          </div>

          <div
            v-if="field.type === 'labels' || field.type === 'select'"
            class="options-block"
          >
            <div class="options-header">
              <span>{{ field.type === 'labels' ? 'Label options' : 'Choices' }}</span>
              <button type="button" class="link-btn" @click="addOption(activeTab, index)">
                + Add option
              </button>
            </div>
            <div v-if="!(field.options?.length)" class="options-empty">
              No options yet. Add at least one.
            </div>
            <div v-for="(option, optionIndex) in field.options ?? []" :key="optionIndex" class="option-row">
              <input
                :value="option"
                type="text"
                placeholder="Option label"
                @input="field.options![optionIndex] = ($event.target as HTMLInputElement).value"
              />
              <button
                type="button"
                class="tiny-btn danger"
                @click="removeOption(activeTab, index, optionIndex)"
              >
                ×
              </button>
            </div>
          </div>

          <p class="preview-line">
            Preview default:
            <code>{{ JSON.stringify(fieldDefaultValue(field)) }}</code>
          </p>
        </article>

        <button type="button" class="add-field-btn" @click="addField(activeTab)">
          + Add {{ activeTab === 'message' ? 'message' : 'conversation' }} field
        </button>
      </div>

      <footer class="editor-footer">
        <button type="button" class="btn btn-secondary" @click="emit('close')">Cancel</button>
        <button type="button" class="btn btn-primary" :disabled="saving" @click="handleSave">
          {{ saving ? 'Saving…' : 'Apply & save template' }}
        </button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.schema-editor-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.schema-editor {
  width: min(760px, 100%);
  max-height: min(90vh, 900px);
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem 1.5rem 0.75rem;
  border-bottom: 1px solid #eef2f7;
}

.editor-header h2 {
  margin: 0 0 0.35rem;
  font-size: 1.2rem;
}

.editor-header p {
  margin: 0;
  color: var(--muted);
  font-size: 0.9rem;
}

.icon-btn {
  border: none;
  background: #f1f5f9;
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
}

.tab-row {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid #eef2f7;
}

.tab-btn {
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 999px;
  padding: 0.35rem 0.85rem;
  font-size: 0.85rem;
  cursor: pointer;
}

.tab-btn.active {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
  font-weight: 600;
}

.fields-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.field-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.85rem;
  background: #fafbfc;
}

.field-card-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.65rem;
}

.field-index {
  font-size: 0.75rem;
  font-weight: 700;
  color: #64748b;
}

.toolbar-actions {
  display: flex;
  gap: 0.35rem;
}

.tiny-btn {
  border: 1px solid #cbd5e1;
  background: white;
  border-radius: 8px;
  padding: 0.15rem 0.45rem;
  font-size: 0.75rem;
  cursor: pointer;
}

.tiny-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tiny-btn.danger {
  color: #b91c1c;
  border-color: #fecaca;
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
}

.field-grid label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field-grid label span {
  font-size: 0.72rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.field-grid input,
.field-grid select {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0.45rem 0.55rem;
  font: inherit;
}

.full-width {
  grid-column: 1 / -1;
}

.options-block {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px dashed #dbe3ee;
}

.options-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: #475569;
}

.link-btn {
  border: none;
  background: none;
  color: var(--primary);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}

.options-empty {
  font-size: 0.82rem;
  color: #94a3b8;
  font-style: italic;
}

.option-row {
  display: flex;
  gap: 0.35rem;
  margin-bottom: 0.35rem;
}

.option-row input {
  flex: 1;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0.4rem 0.55rem;
  font: inherit;
}

.preview-line {
  margin: 0.65rem 0 0;
  font-size: 0.75rem;
  color: #94a3b8;
}

.preview-line code {
  font-size: 0.72rem;
}

.add-field-btn {
  border: 1px dashed #93c5fd;
  background: #f8fbff;
  color: #1d4ed8;
  border-radius: 12px;
  padding: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}

.editor-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
  padding: 0.85rem 1.5rem 1.25rem;
  border-top: 1px solid #eef2f7;
}
</style>
