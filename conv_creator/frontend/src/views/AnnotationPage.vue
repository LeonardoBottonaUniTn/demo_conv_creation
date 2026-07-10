<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Dropdown from 'primevue/dropdown'
import FileSelectorModal from '../components/shared/FileSelectorModal.vue'
import AnnotationFieldInput from '../components/annotation/AnnotationFieldInput.vue'
import AnnotationSchemaEditor from '../components/annotation/AnnotationSchemaEditor.vue'
import { useAnnotations } from '../composables/useAnnotations'
import { getSpeakerColors } from '../composables/useSpeakerColors'
import type { AnnotationSchema } from '../types/annotation'
import type { ChatMessage } from '../types/chat'

const route = useRoute()
const router = useRouter()

const {
  filePath,
  messages,
  schema,
  messageFields,
  conversationFields,
  annotations,
  loading,
  saving,
  schemaSaving,
  error,
  schemaError,
  dirty,
  annotatedCount,
  progressPercent,
  loadFile,
  save,
  applySchema,
  getMessageFieldValue,
  getConversationFieldValue,
  isMessageAnnotated,
  getDisplayLabelsForMessage,
  updateMessageFieldValue,
  updateConversationFieldValue,
  updateStatus,
} = useAnnotations()

const showFileSelector = ref(false)
const showSchemaEditor = ref(false)
const selectedMessageId = ref<number | null>(null)
const saveMessage = ref<string | null>(null)
const schemaMessage = ref<string | null>(null)

const currentFile = computed(() => {
  const p = route.params.file as string | undefined
  const q = route.query.file as string | undefined
  return p || q || undefined
})

const selectedMessage = computed(() =>
  messages.value.find((m) => m.id === selectedMessageId.value) ?? null,
)

const statusOptions = [
  { label: 'Not started', value: 'not_started' },
  { label: 'In progress', value: 'in_progress' },
  { label: 'Completed', value: 'completed' },
]

function selectMessage(message: ChatMessage) {
  selectedMessageId.value = message.id
}

function selectNextUnannotated() {
  const next = messages.value.find((m) => !isMessageAnnotated(m.id))
  if (next) selectedMessageId.value = next.id
}

function onFileSelected(path: string) {
  showFileSelector.value = false
  router.replace({ name: 'annotate', query: { file: path } })
}

async function handleSave() {
  saveMessage.value = null
  const ok = await save()
  saveMessage.value = ok ? 'Labels saved.' : 'Save failed.'
  if (ok) setTimeout(() => (saveMessage.value = null), 3000)
}

async function handleSchemaSave(nextSchema: AnnotationSchema) {
  schemaMessage.value = null
  applySchema(nextSchema, true)
  showSchemaEditor.value = false
  schemaMessage.value = 'Labeling template updated.'
  setTimeout(() => (schemaMessage.value = null), 3000)
}

watch(currentFile, async (path) => {
  if (path) {
    await loadFile(path)
    if (messages.value.length > 0 && selectedMessageId.value === null) {
      selectedMessageId.value = messages.value[0].id
    }
  } else {
    showFileSelector.value = true
  }
})

onMounted(async () => {
  if (currentFile.value) {
    await loadFile(currentFile.value)
    if (messages.value.length > 0) {
      selectedMessageId.value = messages.value[0].id
    }
  } else {
    showFileSelector.value = true
  }
})
</script>

<template>
  <div class="annotation-page">
    <header class="page-header">
      <div class="header-left">
        <h1>Label Conversation</h1>
        <p v-if="filePath" class="file-name">{{ filePath }}</p>
        <p v-else class="file-name muted">No file selected</p>
      </div>

      <div class="header-right">
        <div v-if="messages.length > 0" class="progress-block">
          <span class="progress-label">
            {{ annotatedCount }} / {{ messages.length }} labeled ({{ progressPercent }}%)
          </span>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: `${progressPercent}%` }"></div>
          </div>
        </div>

        <button class="btn btn-secondary" type="button" @click="showSchemaEditor = true">
          Customize fields
        </button>
        <button class="btn btn-secondary" type="button" @click="showFileSelector = true">
          Change file
        </button>
        <button
          class="btn btn-primary"
          type="button"
          :disabled="!filePath || saving || !dirty"
          @click="handleSave"
        >
          {{ saving ? 'Saving…' : 'Save labels' }}
        </button>
      </div>
    </header>

    <div v-if="error" class="banner error">{{ error }}</div>
    <div v-if="schemaError" class="banner error">{{ schemaError }}</div>
    <div v-if="saveMessage" class="banner success">{{ saveMessage }}</div>
    <div v-if="schemaMessage" class="banner success">{{ schemaMessage }}</div>

    <div v-if="loading" class="state-panel">Loading conversation…</div>

    <div v-else-if="!filePath" class="state-panel">
      <p>Select a draft conversation file to begin labeling.</p>
      <button class="btn btn-primary" type="button" @click="showFileSelector = true">
        Select file
      </button>
    </div>

    <div v-else-if="messages.length === 0" class="state-panel">
      <p>This file has no conversation messages to label.</p>
      <button class="btn btn-secondary" type="button" @click="showFileSelector = true">
        Choose another file
      </button>
    </div>

    <div v-else class="annotation-layout">
      <section class="messages-panel">
        <div class="panel-title">
          <h2>Messages</h2>
          <button class="link-btn" type="button" @click="selectNextUnannotated">
            Next unlabeled
          </button>
        </div>

        <div class="messages-list">
          <article
            v-for="(message, index) in messages"
            :key="message.id"
            class="message-card"
            :class="{
              selected: selectedMessageId === message.id,
              annotated: isMessageAnnotated(message.id),
            }"
            @click="selectMessage(message)"
          >
            <div class="message-card-header">
              <span
                class="speaker"
                :style="{ color: getSpeakerColors(message.speaker).color }"
              >
                {{ message.speaker }}
              </span>
              <span class="turn">Turn {{ index + 1 }}</span>
              <span v-if="isMessageAnnotated(message.id)" class="annotated-badge">✓</span>
            </div>
            <p class="message-text">{{ message.text }}</p>
            <div v-if="getDisplayLabelsForMessage(message.id).length > 0" class="label-chips">
              <span
                v-for="label in getDisplayLabelsForMessage(message.id)"
                :key="label"
                class="chip"
              >
                {{ label }}
              </span>
            </div>
          </article>
        </div>
      </section>

      <section class="annotation-panel">
        <div class="panel-title">
          <h2>Labeling</h2>
        </div>

        <div v-if="!selectedMessage" class="empty-annotation">
          Select a message to label it.
        </div>

        <template v-else>
          <div class="selected-message-preview">
            <div class="preview-header">
              <span
                class="speaker"
                :style="{ color: getSpeakerColors(selectedMessage.speaker).color }"
              >
                {{ selectedMessage.speaker }}
              </span>
            </div>
            <p>{{ selectedMessage.text }}</p>
          </div>

          <AnnotationFieldInput
            v-for="field in messageFields"
            :key="field.id"
            :field="field"
            :model-value="getMessageFieldValue(selectedMessage.id, field.id)"
            @update:model-value="
              (value) => updateMessageFieldValue(selectedMessage!.id, field.id, value)
            "
          />

          <p v-if="messageFields.length === 0" class="empty-fields-note">
            No message fields configured.
            <button type="button" class="link-btn" @click="showSchemaEditor = true">
              Add fields
            </button>
          </p>
        </template>

        <div class="conversation-meta">
          <h3>Conversation-level</h3>

          <div class="field">
            <label>Status</label>
            <Dropdown
              :model-value="annotations.status"
              :options="statusOptions"
              option-label="label"
              option-value="value"
              class="annotation-dropdown"
              @update:model-value="(val) => updateStatus(val)"
            />
          </div>

          <AnnotationFieldInput
            v-for="field in conversationFields"
            :key="field.id"
            :field="field"
            :model-value="getConversationFieldValue(field.id)"
            @update:model-value="(value) => updateConversationFieldValue(field.id, value)"
          />

          <p v-if="conversationFields.length === 0" class="empty-fields-note">
            No conversation fields configured.
          </p>

          <p v-if="annotations.updatedAt" class="meta-line">
            Last saved: {{ new Date(annotations.updatedAt).toLocaleString() }}
          </p>
        </div>
      </section>
    </div>

    <FileSelectorModal
      v-if="showFileSelector"
      title="Select a draft conversation"
      confirm-label="Open for labeling"
      @select="onFileSelected"
      @close="showFileSelector = false"
    />

    <AnnotationSchemaEditor
      v-if="showSchemaEditor"
      :model-value="schema"
      :saving="schemaSaving"
      @save="handleSchemaSave"
      @close="showSchemaEditor = false"
    />
  </div>
</template>

<style scoped>
.annotation-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 1.25rem 2rem 2rem;
  overflow: hidden;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.5rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.header-left h1 {
  margin: 0 0 0.25rem;
  font-size: 1.5rem;
  color: var(--text-900);
}

.file-name {
  margin: 0;
  font-size: 0.9rem;
  color: var(--muted);
}

.file-name.muted {
  font-style: italic;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.progress-block {
  min-width: 180px;
}

.progress-label {
  display: block;
  font-size: 0.8rem;
  color: var(--muted);
  margin-bottom: 0.25rem;
}

.progress-bar {
  height: 6px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3498db, #2ecc71);
  border-radius: 999px;
  transition: width 0.25s ease;
}

.banner {
  padding: 0.65rem 1rem;
  border-radius: 10px;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
}

.banner.error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.banner.success {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.state-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: var(--muted);
}

.annotation-layout {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 1rem;
  min-height: 0;
}

.messages-panel,
.annotation-panel {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  box-shadow: var(--shadow-sm);
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid #eef2f7;
}

.panel-title h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-900);
}

.link-btn {
  border: none;
  background: none;
  color: var(--primary);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}

.link-btn:hover {
  text-decoration: underline;
}

.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.message-card {
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 0.75rem;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.message-card:hover {
  border-color: #cbd5e1;
}

.message-card.selected {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.15);
}

.message-card.annotated {
  border-left: 3px solid #22c55e;
}

.message-card-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.speaker {
  font-weight: 700;
  font-size: 0.9rem;
}

.turn {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-left: auto;
}

.annotated-badge {
  color: #16a34a;
  font-weight: 700;
  font-size: 0.85rem;
}

.message-text {
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.45;
  color: var(--text-700);
}

.label-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.5rem;
}

.chip {
  font-size: 0.72rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 600;
}

.annotation-panel {
  overflow-y: auto;
  padding: 0 1rem 1rem;
}

.empty-annotation {
  padding: 2rem 0;
  text-align: center;
  color: var(--muted);
  font-size: 0.9rem;
}

.empty-fields-note {
  font-size: 0.85rem;
  color: var(--muted);
  margin: 0 0 1rem;
}

.selected-message-preview {
  background: #f8fafc;
  border-radius: 10px;
  padding: 0.75rem;
  margin-bottom: 1rem;
  border: 1px solid #e2e8f0;
}

.preview-header {
  margin-bottom: 0.35rem;
}

.selected-message-preview p {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.45;
  color: var(--text-700);
}

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

.conversation-meta {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #eef2f7;
}

.conversation-meta h3 {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  color: var(--text-900);
}

.meta-line {
  margin: 0;
  font-size: 0.78rem;
  color: #94a3b8;
}

:deep(.annotation-dropdown) {
  width: 100%;
}

@media (max-width: 960px) {
  .annotation-layout {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .annotation-page {
    overflow-y: auto;
  }

  .messages-panel {
    max-height: 50vh;
  }
}
</style>
