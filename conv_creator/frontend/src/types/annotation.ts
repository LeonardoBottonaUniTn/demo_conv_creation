export type AnnotationFieldType =
  | 'labels'
  | 'text'
  | 'textarea'
  | 'rating'
  | 'select'
  | 'number'

export type AnnotationFieldScope = 'message' | 'conversation'

export interface AnnotationFieldDefinition {
  id: string
  label: string
  type: AnnotationFieldType
  /** Options for labels / select fields */
  options?: string[]
  placeholder?: string
  required?: boolean
}

export interface AnnotationSchema {
  version: 1
  messageFields: AnnotationFieldDefinition[]
  conversationFields: AnnotationFieldDefinition[]
}

export interface MessageAnnotation {
  messageId: number
  values: Record<string, unknown>
}

export interface ConversationAnnotations {
  status: 'not_started' | 'in_progress' | 'completed'
  schema?: AnnotationSchema
  conversationValues: Record<string, unknown>
  updatedAt: string | null
  messages: MessageAnnotation[]
}

export const DEFAULT_LABEL_OPTIONS = [
  'Support',
  'Attack',
  'Question',
  'Clarification',
  'Neutral',
  'Off-topic',
]

export const DEFAULT_ANNOTATION_SCHEMA: AnnotationSchema = {
  version: 1,
  messageFields: [
    {
      id: 'labels',
      label: 'Labels',
      type: 'labels',
      options: [...DEFAULT_LABEL_OPTIONS],
    },
    {
      id: 'rating',
      label: 'Quality rating',
      type: 'rating',
    },
    {
      id: 'note',
      label: 'Notes',
      type: 'textarea',
      placeholder: 'Add notes about this turn (stance, argument type, issues…)',
    },
  ],
  conversationFields: [
    {
      id: 'overallNote',
      label: 'Overall notes',
      type: 'textarea',
      placeholder: 'Summary, quality assessment, or remarks about the whole conversation',
    },
  ],
}

export function cloneSchema(schema: AnnotationSchema): AnnotationSchema {
  return {
    version: 1,
    messageFields: schema.messageFields.map((f) => ({
      ...f,
      options: f.options ? [...f.options] : undefined,
    })),
    conversationFields: schema.conversationFields.map((f) => ({
      ...f,
      options: f.options ? [...f.options] : undefined,
    })),
  }
}

export function normalizeSchema(raw: unknown): AnnotationSchema {
  if (!raw || typeof raw !== 'object') return cloneSchema(DEFAULT_ANNOTATION_SCHEMA)

  const obj = raw as Record<string, unknown>
  const normalizeField = (f: unknown): AnnotationFieldDefinition | null => {
    if (!f || typeof f !== 'object') return null
    const field = f as Record<string, unknown>
    const type = field.type as AnnotationFieldType
    const validTypes: AnnotationFieldType[] = [
      'labels',
      'text',
      'textarea',
      'rating',
      'select',
      'number',
    ]
    if (!validTypes.includes(type)) return null

    const id = typeof field.id === 'string' ? field.id.trim() : ''
    const label = typeof field.label === 'string' ? field.label.trim() : ''
    if (!id || !label) return null

    const options = Array.isArray(field.options)
      ? field.options.map(String).filter((o) => o.trim()).map((o) => o.trim())
      : undefined

    return {
      id,
      label,
      type,
      options: type === 'labels' || type === 'select' ? options ?? [] : options,
      placeholder: typeof field.placeholder === 'string' ? field.placeholder : undefined,
      required: field.required === true,
    }
  }

  const messageFields = Array.isArray(obj.messageFields)
    ? obj.messageFields.map(normalizeField).filter((f): f is AnnotationFieldDefinition => f !== null)
    : []
  const conversationFields = Array.isArray(obj.conversationFields)
    ? obj.conversationFields
        .map(normalizeField)
        .filter((f): f is AnnotationFieldDefinition => f !== null)
    : []

  if (messageFields.length === 0 && conversationFields.length === 0) {
    return cloneSchema(DEFAULT_ANNOTATION_SCHEMA)
  }

  return { version: 1, messageFields, conversationFields }
}

export function emptyMessageAnnotation(messageId: number): MessageAnnotation {
  return { messageId, values: {} }
}

export function emptyConversationAnnotations(schema?: AnnotationSchema): ConversationAnnotations {
  return {
    status: 'not_started',
    schema: schema ? cloneSchema(schema) : undefined,
    conversationValues: {},
    updatedAt: null,
    messages: [],
  }
}

export function fieldDefaultValue(field: AnnotationFieldDefinition): unknown {
  switch (field.type) {
    case 'labels':
      return []
    case 'rating':
    case 'select':
    case 'number':
      return null
    default:
      return ''
  }
}

export function isFieldValueEmpty(field: AnnotationFieldDefinition, value: unknown): boolean {
  if (value === null || value === undefined) return true
  switch (field.type) {
    case 'labels':
      return !Array.isArray(value) || value.length === 0
    case 'text':
    case 'textarea':
      return typeof value !== 'string' || value.trim().length === 0
    case 'rating':
    case 'select':
    case 'number':
      return value === null || value === ''
    default:
      return true
  }
}

export function isMessageAnnotationFilled(
  annotation: MessageAnnotation,
  fields: AnnotationFieldDefinition[],
): boolean {
  return fields.some((field) => !isFieldValueEmpty(field, annotation.values[field.id]))
}

export function isConversationAnnotationFilled(
  conversationValues: Record<string, unknown>,
  fields: AnnotationFieldDefinition[],
): boolean {
  return fields.some((field) => !isFieldValueEmpty(field, conversationValues[field.id]))
}

/** Migrate legacy fixed-field annotations to schema-driven values. */
export function migrateLegacyMessageAnnotation(raw: Record<string, unknown>): MessageAnnotation {
  const messageId = Number(raw.messageId)
  const values: Record<string, unknown> =
    raw.values && typeof raw.values === 'object' && !Array.isArray(raw.values)
      ? { ...(raw.values as Record<string, unknown>) }
      : {}

  if (!values.labels && Array.isArray(raw.labels)) values.labels = raw.labels.map(String)
  if (values.note === undefined && typeof raw.note === 'string') values.note = raw.note
  if (values.rating === undefined && typeof raw.rating === 'number') values.rating = raw.rating

  return { messageId, values }
}

export function migrateLegacyConversationAnnotations(
  raw: Record<string, unknown>,
  fallbackSchema?: AnnotationSchema,
): ConversationAnnotations {
  const status =
    raw.status === 'completed' || raw.status === 'in_progress' || raw.status === 'not_started'
      ? raw.status
      : 'not_started'

  const schema = raw.schema ? normalizeSchema(raw.schema) : fallbackSchema

  const conversationValues: Record<string, unknown> =
    raw.conversationValues &&
    typeof raw.conversationValues === 'object' &&
    !Array.isArray(raw.conversationValues)
      ? { ...(raw.conversationValues as Record<string, unknown>) }
      : {}

  if (
    conversationValues.overallNote === undefined &&
    typeof raw.overallNote === 'string'
  ) {
    conversationValues.overallNote = raw.overallNote
  }

  const messages = Array.isArray(raw.messages)
    ? raw.messages
        .filter((m): m is Record<string, unknown> => m && typeof m === 'object')
        .map(migrateLegacyMessageAnnotation)
    : []

  return {
    status,
    schema: schema ? cloneSchema(schema) : undefined,
    conversationValues,
    updatedAt: typeof raw.updatedAt === 'string' ? raw.updatedAt : null,
    messages,
  }
}

export function slugifyFieldId(label: string, existingIds: Set<string>): string {
  const base =
    label
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '') || 'field'

  let candidate = base
  let counter = 2
  while (existingIds.has(candidate)) {
    candidate = `${base}_${counter}`
    counter += 1
  }
  return candidate
}
