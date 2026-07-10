import { ref, computed } from 'vue'
import { useAuthFetch } from './useAuthFetch'
import type { ChatMessage } from '../types/chat'
import {
  type AnnotationFieldDefinition,
  type AnnotationSchema,
  type ConversationAnnotations,
  type MessageAnnotation,
  DEFAULT_ANNOTATION_SCHEMA,
  cloneSchema,
  emptyConversationAnnotations,
  emptyMessageAnnotation,
  isConversationAnnotationFilled,
  isFieldValueEmpty,
  isMessageAnnotationFilled,
  migrateLegacyConversationAnnotations,
  normalizeSchema,
} from '../types/annotation'

const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

export function useAnnotations() {
  const { authFetch } = useAuthFetch()

  const filePath = ref<string | null>(null)
  const fileId = ref<string | null>(null)
  const messages = ref<ChatMessage[]>([])
  const rawFile = ref<Record<string, unknown> | null>(null)
  const schema = ref<AnnotationSchema>(cloneSchema(DEFAULT_ANNOTATION_SCHEMA))
  const annotations = ref<ConversationAnnotations>(emptyConversationAnnotations(schema.value))
  const loading = ref(false)
  const saving = ref(false)
  const schemaSaving = ref(false)
  const error = ref<string | null>(null)
  const schemaError = ref<string | null>(null)
  const dirty = ref(false)

  const messageFields = computed(() => schema.value.messageFields)
  const conversationFields = computed(() => schema.value.conversationFields)

  const annotatedCount = computed(() => {
    return annotations.value.messages.filter((a) =>
      isMessageAnnotationFilled(a, messageFields.value),
    ).length
  })

  const progressPercent = computed(() => {
    if (messages.value.length === 0) return 0
    return Math.round((annotatedCount.value / messages.value.length) * 100)
  })

  function getAnnotationForMessage(messageId: number): MessageAnnotation {
    let entry = annotations.value.messages.find((a) => a.messageId === messageId)
    if (!entry) {
      entry = emptyMessageAnnotation(messageId)
      annotations.value.messages.push(entry)
    }
    return entry
  }

  function getMessageFieldValue(messageId: number, fieldId: string): unknown {
    return getAnnotationForMessage(messageId).values[fieldId]
  }

  function getConversationFieldValue(fieldId: string): unknown {
    return annotations.value.conversationValues[fieldId]
  }

  function isMessageAnnotated(messageId: number): boolean {
    const entry = annotations.value.messages.find((a) => a.messageId === messageId)
    if (!entry) return false
    return isMessageAnnotationFilled(entry, messageFields.value)
  }

  function getDisplayLabelsForMessage(messageId: number): string[] {
    const entry = getAnnotationForMessage(messageId)
    const chips: string[] = []

    for (const field of messageFields.value) {
      const value = entry.values[field.id]
      if (field.type === 'labels' && Array.isArray(value) && value.length > 0) {
        chips.push(...value.map(String))
        continue
      }
      if (field.type === 'select' && value !== null && value !== undefined && value !== '') {
        chips.push(String(value))
        continue
      }
      if (field.type === 'rating' && typeof value === 'number') {
        chips.push(`${field.label}: ${value}`)
      }
    }

    return chips
  }

  function parseDiscussion(raw: Record<string, unknown>): ChatMessage[] {
    const discussion = raw.discussion
    if (!Array.isArray(discussion) || discussion.length === 0) return []

    return discussion.map((d: any, i: number) => ({
      id: typeof d.id === 'number' ? d.id : i + 1,
      referenceId: String(d.referenceId || d.node?.id || d.id || ''),
      speaker: String(d.speaker || d.from || d.author || 'Unknown'),
      text: String(d.text || d.body || d.content || ''),
      addressees: Array.isArray(d.addressees) ? d.addressees : d.to ? [d.to] : [],
    }))
  }

  function parseAnnotations(
    raw: Record<string, unknown>,
    activeSchema: AnnotationSchema,
  ): ConversationAnnotations {
    const stored = raw.annotations
    if (!stored || typeof stored !== 'object') {
      return emptyConversationAnnotations(activeSchema)
    }

    const parsed = migrateLegacyConversationAnnotations(
      stored as Record<string, unknown>,
      activeSchema,
    )
    if (!parsed.schema) parsed.schema = cloneSchema(activeSchema)
    return parsed
  }

  async function loadUserSchema(): Promise<AnnotationSchema> {
    const resp = await authFetch(`${API_BASE}/api/settings/annotation-schema`)
    if (!resp.ok) return cloneSchema(DEFAULT_ANNOTATION_SCHEMA)
    const data = await resp.json()
    return normalizeSchema(data?.schema)
  }

  async function saveUserSchema(nextSchema: AnnotationSchema): Promise<boolean> {
    schemaSaving.value = true
    schemaError.value = null
    try {
      const resp = await authFetch(`${API_BASE}/api/settings/annotation-schema`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ schema: nextSchema }),
      })
      if (!resp.ok) {
        const detail = await resp.text()
        throw new Error(detail || `Schema save failed (${resp.status})`)
      }
      const data = await resp.json()
      schema.value = normalizeSchema(data?.schema)
      annotations.value.schema = cloneSchema(schema.value)
      return true
    } catch (err: unknown) {
      schemaError.value = err instanceof Error ? err.message : String(err)
      return false
    } finally {
      schemaSaving.value = false
    }
  }

  async function loadFile(path: string, id?: string | null) {
    loading.value = true
    error.value = null
    filePath.value = path
    fileId.value = id ?? null
    messages.value = []
    rawFile.value = null
    dirty.value = false

    try {
      const userSchema = await loadUserSchema()
      schema.value = userSchema

      const resp = await authFetch(`${API_BASE}/api/files/${encodeURI(path)}`)
      if (!resp.ok) throw new Error(`Failed to load file (${resp.status})`)

      const raw = await resp.json()
      if (!raw || typeof raw !== 'object') throw new Error('Invalid file content')

      rawFile.value = raw
      const parsed = parseDiscussion(raw)
      if (parsed.length === 0) {
        throw new Error(
          'This file has no conversation messages. Save a draft from the Discussion page first.',
        )
      }

      messages.value = parsed
      annotations.value = parseAnnotations(raw, userSchema)
      if (annotations.value.schema) {
        schema.value = cloneSchema(annotations.value.schema)
      }

      if (
        (annotatedCount.value > 0 ||
          isConversationAnnotationFilled(
            annotations.value.conversationValues,
            conversationFields.value,
          )) &&
        annotations.value.status === 'not_started'
      ) {
        annotations.value.status = 'in_progress'
      }
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      loading.value = false
    }
  }

  function markDirty() {
    dirty.value = true
    if (annotations.value.status === 'not_started') {
      annotations.value.status = 'in_progress'
    }
  }

  function updateMessageFieldValue(messageId: number, fieldId: string, value: unknown) {
    const entry = getAnnotationForMessage(messageId)
    entry.values[fieldId] = value
    markDirty()
  }

  function updateConversationFieldValue(fieldId: string, value: unknown) {
    annotations.value.conversationValues[fieldId] = value
    markDirty()
  }

  function updateStatus(status: ConversationAnnotations['status']) {
    annotations.value.status = status
    markDirty()
  }

  function applySchema(nextSchema: AnnotationSchema, persistAsDefault = true) {
    schema.value = cloneSchema(nextSchema)
    annotations.value.schema = cloneSchema(nextSchema)
    markDirty()
    if (persistAsDefault) {
      void saveUserSchema(nextSchema)
    }
  }

  async function save(): Promise<boolean> {
    if (!filePath.value || !rawFile.value) return false

    saving.value = true
    error.value = null

    try {
      annotations.value.updatedAt = new Date().toISOString()
      annotations.value.schema = cloneSchema(schema.value)
      const payload = {
        ...rawFile.value,
        annotations: annotations.value,
      }

      const resp = await authFetch(`${API_BASE}/api/files/${encodeURI(filePath.value)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!resp.ok) {
        const detail = await resp.text()
        throw new Error(detail || `Save failed (${resp.status})`)
      }

      rawFile.value = payload
      dirty.value = false
      return true
    } catch (err: unknown) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    } finally {
      saving.value = false
    }
  }

  return {
    filePath,
    fileId,
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
    saveUserSchema,
    applySchema,
    getAnnotationForMessage,
    getMessageFieldValue,
    getConversationFieldValue,
    isMessageAnnotated,
    getDisplayLabelsForMessage,
    updateMessageFieldValue,
    updateConversationFieldValue,
    updateStatus,
    isFieldValueEmpty,
  }
}

export type { AnnotationFieldDefinition, AnnotationSchema }
