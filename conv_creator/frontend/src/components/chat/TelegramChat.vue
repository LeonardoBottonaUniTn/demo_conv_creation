<template>
  <!-- TODO: fix line 29-->
  <div class="chat-section">
    <div class="chat-header">
      <h3>{{ title }}</h3>
      <button class="settings-button" @click="openSettings" title="Settings">
        <i class="pi pi-cog" style="font-size: 1.2rem"></i>
      </button>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="(message, index) in localMessages"
        :key="message.id"
        class="message"
        :data-message-id="message.id"
        :class="{
          'own-message': message.speaker === selectedSpeaker,
          'editing-message': message.id === editingMessageId,
          hovered: hoveredMessageId === message.id,
        }"
        @dblclick.prevent="editMessage(message, index)"
        @pointerenter="onMessageHover(message.id, $event)"
        @pointerleave="onMessageLeave(message.id, $event)"
      >
        <div class="message-header">
          <div class="message-meta">
            <span class="speaker" :style="{ color: getSpeakerColors(message.speaker).color }">{{
              message.speaker
            }}</span>
            <span v-if="message.addressees && message.addressees.length > 0" class="addressees">
              →
              <template v-for="(a, ai) in message.addressees" :key="ai">
                <span class="speaker" :style="{ color: getSpeakerColors(a).color }">
                  {{ a }}
                </span>
                <span v-if="ai < message.addressees.length - 1">, </span>
              </template>
            </span>
          </div>
          <span class="turn">Turn {{ index + 1 }}</span>
        </div>
        <div class="message-body">
          <div class="avatar-column">
            <span
              class="user-avatar"
              :style="{
                backgroundColor: getSpeakerColors(message.speaker).color,
                color: getSpeakerColors(message.speaker).onAccent,
              }"
            >
              {{ message.speaker.charAt(0).toUpperCase() }}
            </span>
            <div class="arrow-controls" aria-hidden="true">
              <button
                class="arrow-btn"
                aria-hidden="true"
                @click.stop.prevent="referenceMessage(message, 'up')"
                title="Move up"
                aria-label="Move message up"
              >
                <i class="pi pi-arrow-up" style="font-size: 0.8rem"></i>
              </button>
              <button
                class="arrow-btn"
                aria-hidden="true"
                @click.stop.prevent="referenceMessage(message, 'down')"
                title="Move down"
                aria-label="Move message down"
              >
                <i class="pi pi-arrow-down" style="font-size: 0.8rem"></i>
              </button>
            </div>
          </div>
          <span>
            <div class="message-text" aria-live="polite">
              {{ message.text }}
              <!-- Sparkles / magic button inside the message bubble -->
              <button
                class="message-magic-btn"
                @click.stop.prevent="handleMagicForMessage(message)"
                :title="`Magic for ${message.speaker}`"
                aria-label="Generate magic for this message"
              >
                <i class="pi pi-bolt" style="font-size: 0.8rem"></i>
              </button>
            </div>
          </span>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <ChatInput
        ref="chatInputRef"
        v-model="newMessage"
        :placeholder="inputPlaceholder"
        :selected-speaker="selectedSpeaker"
        :selected-addressees="selectedAddressees"
        style="flex: 1"
        @send="sendMessage"
        @update:speaker="selectSpeaker"
        @update:addressees="selectAddressees"
        @update:modelValue="handleInputUpdate"
      />
      <button
        v-if="editingMessageId !== null"
        class="cancel-edit-btn"
        @click="cancelEdit"
        title="Cancel edit"
      >
        Cancel
      </button>
    </div>

    <!-- Settings Modal -->
    <Modal :is-visible="showSettingsModal" title="Group Description" @close="closeSettings">
      <div class="settings-modal-body">
        <h4>Users in this group</h4>
        <ul class="users-list">
          <li v-for="user in usersList" :key="user" class="user-item">
            <span
              class="user-avatar"
              :style="{
                backgroundColor: getSpeakerColors(user).color,
                color: getSpeakerColors(user).onAccent,
              }"
            >
              {{ user.charAt(0).toUpperCase() }}
            </span>
            <span class="user-name">{{ user }}</span>
            <div class="user-input-row">
              <textarea
                class="user-description-input"
                v-model="descriptions[user]"
                :placeholder="`${user}'s description`"
                @input="updateDescription(user)"
                rows="2"
              ></textarea>
              <button
                class="magic-btn"
                @click="handleMagicForUser(user)"
                :disabled="generatingUsers[user]"
                :title="`Magic fill for ${user}`"
                aria-label="Magic autofill description"
              >
                <template v-if="!generatingUsers[user]">
                  <!-- Inline magic-wand SVG to avoid external dependency -->
                  <i class="pi pi-bolt"></i>
                </template>
                <template v-else>
                  <span class="magic-loading">…</span>
                </template>
              </button>
            </div>
          </li>
        </ul>
      </div>

      <!-- Put Save into the modal footer (bottom-right). Close button removed from footer on request. -->
      <template #footer>
        <div class="settings-footer">
          <button
            class="save-btn"
            :disabled="!isDirtyAny"
            :aria-disabled="!isDirtyAny"
            @click="handleSaveDraft"
            :title="isDirtyAny ? 'Save changes' : 'No changes to save'"
          >
            Save a draft
          </button>
          <button
            class="save-btn"
            :disabled="!isDirtyAny"
            :aria-disabled="!isDirtyAny"
            @click="handleSaveDraft"
            :title="isDirtyAny ? 'Save changes' : 'No changes to save'"
          >
            Export
          </button>
          <span v-if="saveMessage" class="save-message">{{ saveMessage }}</span>
        </div>
      </template>
    </Modal>
    <!-- Save Draft Modal -->
    <Modal :is-visible="showSaveModal" title="Save draft" @close="closeSaveModal">
      <div class="settings-modal-body">
        <label for="draft-name">Draft file name</label>
        <input id="draft-name" class="draft-name-input" v-model="draftName" />
        <h4>Preview</h4>
        <div class="debug-json">
          <pre style="white-space: pre-wrap">{{ lastPayloadPreview }}</pre>
        </div>
      </div>
      <template #footer>
        <div class="settings-footer">
          <button class="save-btn" :disabled="!draftName" @click="confirmSave">Save draft</button>
          <button class="save-btn" @click="closeSaveModal">Cancel</button>
          <span v-if="saveMessage" class="save-message">{{ saveMessage }}</span>
        </div>
      </template>
    </Modal>
    <!-- Generated biography preview & confirm modal -->
    <Modal
      :is-visible="showConfirmModal"
      title="Generated description preview"
      @close="cancelGeneratedBio"
    >
      <div class="settings-modal-body">
        <h4>Preview for {{ confirmCandidateUser }}</h4>
        <div class="debug-json">
          <pre style="white-space: pre-wrap">{{ confirmCandidate }}</pre>
        </div>
      </div>
      <template #footer>
        <div class="settings-footer">
          <button class="save-btn" @click="confirmGeneratedBio">Confirm</button>
          <button class="magic-btn" @click="cancelGeneratedBio">Cancel</button>
        </div>
      </template>
    </Modal>
    <!-- Message Magic Modal: used to refine a single message with parameters -->
    <Modal :is-visible="showMessageMagicModal" title="Refine message" @close="cancelMessageMagic">
      <div class="settings-modal-body">
        <h4>Original message</h4>
        <div class="debug-json" style="margin-bottom: 10px">
          <pre style="white-space: pre-wrap">{{ messageToRefine ? messageToRefine.text : '' }}</pre>
        </div>
        <div v-if="messageMagicPreview" class="preview-block">
          <h4>Preview</h4>
          <div class="debug-json" style="margin-bottom: 10px">
            <pre style="white-space: pre-wrap">{{ messageMagicPreview }}</pre>
          </div>
        </div>

        <div class="magic-params-row">
          <label for="temperament-dropdown">Temperament</label>
          <Dropdown
            v-model="selectedTemperament"
            editable
            :options="temperamentOptions"
            optionLabel="name"
            placeholder="Choose or type temperament"
            class="pv-dropdown"
          />
        </div>

        <div class="magic-params-row">
          <label for="style-dropdown">Style</label>
          <Dropdown
            v-model="selectedStyle"
            editable
            :options="styleOptions"
            optionLabel="name"
            placeholder="Choose or type style"
            class="pv-dropdown"
          />
        </div>

        <div class="magic-params-row">
          <label for="length-dropdown">Length</label>
          <Dropdown
            v-model="selectedLength"
            editable
            :options="lengthOptions"
            optionLabel="name"
            placeholder="Choose or type length"
            class="pv-dropdown"
          />
        </div>
      </div>
      <template #footer>
        <div class="settings-footer">
          <!-- If we already have a preview, show Keep/Decline -->
          <template v-if="messageMagicPreview">
            <button class="save-btn" @click="applyMessageMagic">Keep</button>
            <button class="save-btn" @click="declineMessageMagic">Decline</button>
          </template>
          <template v-else>
            <button
              class="save-btn"
              @click="confirmMessageMagic"
              :disabled="messageMagicLoading"
              :aria-disabled="messageMagicLoading"
              title="Confirm"
            >
              <template v-if="!messageMagicLoading">Confirm</template>
              <template v-else><span class="magic-loading">…</span></template>
            </button>
            <button class="save-btn" @click="cancelMessageMagic">Cancel</button>
          </template>
        </div>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
// Settings button handler (placeholder)
// ...existing code...
import { ref, nextTick, watch, onMounted, computed, reactive, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
//import { BiMagic } from 'oh-vue-icons/icons'
import ChatInput from './components/ChatInput.vue'
import Modal from '../shared/Modal.vue'
import { useUsers } from '../../composables/useUsers'
import { useActiveFile } from '../../composables/useActiveFile'
import { getSpeakerColors } from '@/composables/useSpeakerColors'
import Dropdown from 'primevue/dropdown'

const showSettingsModal = ref(false)
const openSettings = () => {
  console.debug('[TelegramChat] openSettings called')
  showSettingsModal.value = true
}
const closeSettings = () => {
  showSettingsModal.value = false
}

// Load personas from backend so settings modal can show them
const { loadUsers, personas, availablePersonas } = useUsers()

// get current route (safe single call). Some environments may not provide a router;
// in that case `route` will be null and we guard access with optional chaining.
let route: any = null
try {
  route = useRoute()
} catch (e) {
  // If useRoute() fails (no router present), leave route as null
  route = null
}

// Compute users list: prefer backend personas (availablePersonas or personas), otherwise derive from messages
const usersList = computed(() => {
  if (availablePersonas.value && availablePersonas.value.length > 0) {
    return availablePersonas.value.map((p) => p.name)
  }
  if (personas.value && personas.value.length > 0) {
    return personas.value.map((p) => p.name)
  }
  const users = props.messages.map((m) => m.speaker)
  return Array.from(new Set(users))
})

// Reactive map of user descriptions. We prefer descriptions from backend personas when available,
// otherwise start with empty strings so inputs are editable.
const descriptions = reactive<Record<string, string>>({})

// Keep a snapshot of the original descriptions so we can detect changes (dirty state)
const originalDescriptions = reactive<Record<string, string>>({})
const saveMessage = ref('')

// Computed flag: true if any description differs from the original snapshot
const isDirtyAny = computed(() => {
  const keys = Object.keys(descriptions)
  for (const k of keys) {
    if ((descriptions[k] || '') !== (originalDescriptions[k] || '')) return true
  }
  return false
})

const populateDescriptions = () => {
  // Use availablePersonas first
  if (availablePersonas.value && availablePersonas.value.length > 0) {
    availablePersonas.value.forEach((p) => {
      descriptions[p.name] = p.description || ''
      // initialize original snapshot
      originalDescriptions[p.name] = descriptions[p.name]
    })
    return
  }
  if (personas.value && personas.value.length > 0) {
    personas.value.forEach((p) => {
      descriptions[p.name] = p.description || ''
      // initialize original snapshot
      originalDescriptions[p.name] = descriptions[p.name]
    })
    return
  }
  // Fallback: derive from messages
  const users = Array.from(new Set(props.messages.map((m) => m.speaker)))
  users.forEach((u) => {
    if (!(u in descriptions)) descriptions[u] = ''
    if (!(u in originalDescriptions)) originalDescriptions[u] = ''
  })
}

// Update underlying persona entries when a description changes (if they exist)
const updateDescription = (name: string) => {
  const value = descriptions[name] || ''
  const ap = availablePersonas.value && availablePersonas.value.find((p) => p.name === name)
  if (ap) {
    ap.description = value
  }
  const ps = personas.value && personas.value.find((p) => p.name === name)
  if (ps) {
    ps.description = value
  }
}

async function getUserContext(name: string) {
  console.log('Fetching user context for:', name)

  // gather short context from visible messages for this user
  let context: string[] = props.messages.filter((m) => m.speaker === name).map((m) => m.text)
  console.log('Initial context from messages (length):', context.length)
  // If the immediate messages are too short, try to fetch the discussion file and extract more nodes
  console.log('Condition to go to try catch', context.length < 4)
  if (context.length < 4) {
    // Prefer using the already-loaded `fileContent` from the composable. If not present,
    // try to load it now.
    try {
      const target = activeFile.value
      let fileData = fileContent.value
      if (!fileData && target) {
        fileData = await ensureLoaded(target)
      }
      if (fileData) {
        const extracted = getTextsBySpeaker(fileData.tree, name)
        console.log('context type', typeof extracted)
        console.log('context content', extracted)
        if (extracted && extracted.length > 0) context = extracted
        return context
      }
    } catch (e) {
      console.error('Error fetching additional context for user', name, e)
      // continue with whatever we have
    }
  }
}

// Per-user generation (magic) state and helper functions
const generatingUsers = reactive<Record<string, boolean>>({})

// Confirmation modal state for generated bios
const showConfirmModal = ref(false)
const confirmCandidate = ref('')
const confirmCandidateUser = ref('')

const confirmGeneratedBio = () => {
  if (confirmCandidateUser.value) {
    descriptions[confirmCandidateUser.value] = confirmCandidate.value
    // user must explicitly save; we don't modify originalDescriptions here
  }
  showConfirmModal.value = false
  confirmCandidate.value = ''
  confirmCandidateUser.value = ''
}

const cancelGeneratedBio = () => {
  showConfirmModal.value = false
  confirmCandidate.value = ''
  confirmCandidateUser.value = ''
}

// Save-draft modal state
const showSaveModal = ref(false)
const draftName = ref('')
const lastPayload = ref<any>(null)
const lastPayloadPreview = computed(() =>
  lastPayload.value ? JSON.stringify(lastPayload.value, null, 2) : '',
)

const closeSaveModal = () => {
  showSaveModal.value = false
  // keep lastPayload for debugging, but clear name
  draftName.value = ''
}

const confirmSave = async () => {
  if (!draftName.value || !lastPayload.value) return
  const apiBase = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'
  try {
    const resp = await fetch(
      `${apiBase}/api/files/save-draft/${encodeURIComponent(draftName.value)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload: lastPayload.value }),
      },
    )
    if (!resp.ok) {
      const txt = await resp.text()
      throw new Error(txt || `HTTP ${resp.status}`)
    }
    const data = await resp.json()
    saveMessage.value = data?.message || 'Draft saved'
    // close modal after a short delay to show feedback
    setTimeout(() => {
      showSaveModal.value = false
    }, 800)
  } catch (e: any) {
    console.error('Save draft failed', e)
    saveMessage.value = `Save failed: ${e?.message || String(e)}`
  }
}

const handleMagicForUser = async (name: string) => {
  try {
    const context = await getUserContext(name)

    const payload = {
      existing_bio: descriptions[name] || '',
      messages: context,
    }

    console.log('Magic payload for', name, payload)

    const apiBase = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'
    const resp = await fetch(`${apiBase}/api/llm/generate-bio`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!resp.ok) {
      const text = await resp.text()
      throw new Error(text || `HTTP ${resp.status}`)
    }

    const data = await resp.json()
    if (data && data.success && typeof data.bio === 'string') {
      confirmCandidate.value = data.bio.trim()
      confirmCandidateUser.value = name
      showConfirmModal.value = true
    } else {
      throw new Error('Invalid response from server')
    }
  } catch (e: any) {
    console.error('Magic generation failed for', name, e)
    saveMessage.value = `Generation failed: ${e?.message || String(e)}`
    setTimeout(() => (saveMessage.value = ''), 5000)
  } finally {
    generatingUsers[name] = false
  }
}

function getTextsBySpeaker(node: any, speaker: string): string[] {
  let result = []

  if (node.speaker === speaker) {
    result.push(node.text)
  }

  if (node.children && node.children.length > 0) {
    for (const child of node.children) {
      result = result.concat(getTextsBySpeaker(child, speaker))
    }
  }

  return result
}

// Save handler: persist changes to backend `/api/users` and provide feedback.
const handleSaveDraft = async () => {
  const refFile = activeFile.value
  if (!refFile) {
    console.warn('[TelegramChat] No active file; cannot save personas')
    return
  }
  try {
    //get file content
  } catch (error) {}
  const payload = {
    fileRef: refFile,
    users: Object.keys(descriptions).map((speaker) => ({
      speaker,
      description: descriptions[speaker],
    })),
    tree: fileContent.value ? fileContent.value.tree : null,
    // Use the local (possibly edited) message copy so refinements / manual edits
    // performed in the UI are included in the saved draft. Shallow-copy objects
    // to produce a plain JSON-friendly array.
    discussion: (localMessages.value || []).map((m) => ({ ...m })),
  }

  lastPayload.value = payload
  draftName.value = `${refFile || 'draft'}-${new Date().toISOString().replace(/[:.]/g, '-')}`
  showSaveModal.value = true
}

// Keyboard shortcut and navigation protection when settings modal is open
const onKeyDown = (e: KeyboardEvent) => {
  const key = e.key ? e.key.toLowerCase() : ''
  if ((e.ctrlKey || e.metaKey) && key === 's') {
    e.preventDefault()
    if (isDirtyAny.value) handleSaveDraft()
  }
}

const beforeUnloadHandler = (e: BeforeUnloadEvent) => {
  if (isDirtyAny.value) {
    e.preventDefault()
    e.returnValue = ''
    return ''
  }
}

// Attach/detach listeners whenever the modal opens/closes
watch(showSettingsModal, (open) => {
  console.debug(`[TelegramChat] showSettingsModal changed -> ${open}`)
  if (open) {
    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('beforeunload', beforeUnloadHandler)
  } else {
    window.removeEventListener('keydown', onKeyDown)
    window.removeEventListener('beforeunload', beforeUnloadHandler)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('beforeunload', beforeUnloadHandler)
})

interface ChatMessage {
  id: number
  referenceId?: string
  speaker: string
  text: string
  addressees?: string[]
}

interface Props {
  messages: ChatMessage[]
  title?: string
  status?: string
  inputPlaceholder?: string
  inputValue?: string
  file?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Discussion Chat',
  inputPlaceholder: 'Type a message...',
  inputValue: '',
})

// Local reactive copy of messages so we can optimistically update the UI when editing
const localMessages = ref<ChatMessage[]>([])

// Initialize localMessages and keep it in sync with prop changes
onMounted(() => {
  localMessages.value = (props.messages || []).slice()
})

watch(
  () => props.messages,
  (newMsgs) => {
    // replace array shallowly to keep reactivity predictable
    localMessages.value = (newMsgs || []).slice()
  },
  { deep: true },
)

// Shared active file and file content via composable
const { activeFile, fileContent, loadFile, ensureLoaded } = useActiveFile()

// Determine desired active file based on prop / router (same priority as before)
const desiredActiveFileRef = computed(() => {
  const p = (props as any).file as string | undefined
  const param = (route?.params?.file as string) || undefined
  const query = (route?.query?.file as string) || undefined
  return p || param || query || undefined
})

// whenever the desired active file changes, try to load it into the shared composable
watch(
  desiredActiveFileRef,
  (val) => {
    if (!val) return
    // If the composable already has the content for this file, skip loading again
    if (fileContent.value && activeFile.value === val) return
    ensureLoaded(val).catch((e) => console.warn('[TelegramChat] ensureLoaded failed', e))
  },
  { immediate: true },
)

const emit = defineEmits<{
  sendMessage: [
    message: { speaker: string; text: string; addressees: string[]; referenceId?: string },
  ]
  editMessage: [
    message: {
      id: number
      speaker: string
      text: string
      addressees: string[]
      referenceId?: string
    },
  ]
  updateInput: [value: string]
  'update:speaker': [speaker: string]
  'update:addressees': [addressees: string[]]
  rewriteMessage: [
    payload: {
      id: number
      speaker: string
      originalText: string
      temperament: string
      style: string
      length: string
    },
  ]
}>()

const newMessage = ref('')
const messagesContainer = ref<HTMLElement>()
const editingMessageId = ref<number | null>(null)
const chatInputRef = ref<any>(null)
const selectedSpeaker = ref<string | null>(null)
const selectedAddressees = ref<string[]>([])
const selectedReferenceId = ref<string | null>(null)

// Watch for external input value changes
watch(
  () => props.inputValue,
  (newVal) => {
    newMessage.value = newVal || ''
  },
)

// Initialize with prop value
onMounted(() => {
  newMessage.value = props.inputValue || ''
  // Populate personas from backend (will use discussion file users via /api/users)
  console.debug(
    '[TelegramChat] onMounted: loading users for active file',
    desiredActiveFileRef.value,
  )
  if (desiredActiveFileRef.value) {
    // The watcher (with immediate:true) will load the file into the composable.
    // Here we only load personas; populateDescriptions will pick up personas when available.
    loadUsers(desiredActiveFileRef.value as string)
      .then(() => {
        populateDescriptions()
      })
      .catch((e) => console.warn('Failed to load personas for settings modal:', e))
  } else {
    console.warn('[TelegramChat] No active discussion file; skipping loadUsers')
  }
})

// Keep descriptions in sync if availablePersonas or personas change
watch([availablePersonas, personas], () => {
  populateDescriptions()
})

const sendMessage = () => {
  if (!selectedSpeaker.value || !newMessage.value.trim() || selectedAddressees.value.length === 0) {
    // Do nothing, speaker must be selected, message not empty, and at least one addresseee selected
    return
  }

  const payloadBase = {
    speaker: selectedSpeaker.value,
    text: newMessage.value,
    addressees: selectedAddressees.value,
    referenceId: selectedReferenceId.value || undefined,
  }

  if (editingMessageId.value !== null) {
    // We're editing an existing message: emit editMessage with id so parent can update in place
    emit('editMessage', { id: editingMessageId.value, ...payloadBase })
    // Optimistically update localMessages so UI reflects change immediately
    const idx = localMessages.value.findIndex((m) => m.id === editingMessageId.value)
    if (idx !== -1) {
      localMessages.value[idx] = {
        ...localMessages.value[idx],
        id: editingMessageId.value,
        ...payloadBase,
      }
    }
    // clear editing state
    editingMessageId.value = null
  } else {
    console.debug(
      '[TelegramChat] sendMessage called. editingMessageId=',
      editingMessageId.value,
      ' payload:',
      payloadBase,
    )
    // Normal send flow
    emit('sendMessage', payloadBase)
  }

  // clear input and notify parent
  newMessage.value = ''
  emit('updateInput', '')

  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const selectSpeaker = (speaker: string) => {
  selectedSpeaker.value = speaker
}

const selectAddressees = (addressees: string[]) => {
  selectedAddressees.value = addressees
}

const handleInputUpdate = (value: string) => {
  newMessage.value = value
  emit('updateInput', value)
}

const removeSpeaker = () => {
  selectedSpeaker.value = null
}

const cancelEdit = () => {
  // clear editing state and notify parent/components
  editingMessageId.value = null
  newMessage.value = ''
  selectedSpeaker.value = null
  selectedAddressees.value = []
  selectedReferenceId.value = null
  ;(emit as any)('update:speaker', selectedSpeaker.value)
  ;(emit as any)('update:addressees', selectedAddressees.value)
  emit('updateInput', newMessage.value)

  // focus input so user can continue typing a new message
  nextTick(() => {
    try {
      const inst: any = chatInputRef.value
      const root = inst?.$el || inst
      if (root && typeof root.querySelector === 'function') {
        const inputEl = root.querySelector('textarea, input, .message-input')
        if (inputEl && typeof inputEl.focus === 'function') inputEl.focus()
      }
    } catch (e) {
      console.debug('[TelegramChat] cancelEdit: focus failed', e)
    }
  })
}

// Keyboard handler active while editing: Escape cancels edit
const onEditKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' || e.key === 'Esc') {
    if (editingMessageId.value !== null) {
      cancelEdit()
    }
  }
}

watch(editingMessageId, (val) => {
  if (val !== null) {
    window.addEventListener('keydown', onEditKeyDown)
  } else {
    window.removeEventListener('keydown', onEditKeyDown)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onEditKeyDown)
})

/**
 * Put an existing message back into the input for editing.
 * The message stays in the chat; this just populates the input + speaker/addressees.
 */
const editMessage = async (message: ChatMessage, _index: number) => {
  // mark which message we are editing so sendMessage can emit editMessage
  editingMessageId.value = message.id
  selectedSpeaker.value = message.speaker
  selectedAddressees.value = Array.isArray(message.addressees) ? [...message.addressees] : []
  console.log('Selected addressees: ', selectedAddressees.value)

  newMessage.value = message.text || ''

  // notify parent/listeners about the selection change and input update
  ;(emit as any)('update:speaker', selectedSpeaker.value)
  ;(emit as any)('update:addressees', selectedAddressees.value)
  emit('updateInput', newMessage.value)

  // give ChatInput a tick to update then focus its input if possible
  await nextTick()
  try {
    const inst: any = chatInputRef.value
    const root = inst?.$el || inst
    if (root && typeof root.querySelector === 'function') {
      const inputEl = root.querySelector('textarea, input, .message-input')
      if (inputEl && typeof inputEl.focus === 'function') inputEl.focus()
    }
  } catch (e) {
    // non-fatal: focusing is a nicety
    console.debug('[TelegramChat] editMessage: focus failed', e)
  }
}

// Reference a message (handler used by arrow controls) — moves message up/down
const referenceMessage = (message: ChatMessage, direction: 'up' | 'down') => {
  const idx = localMessages.value.findIndex((m) => m.id === message.id)
  if (idx === -1) return

  // set selection to the referenced message id (do NOT change selected speaker)
  selectedReferenceId.value = message.referenceId || String(message.id)

  const msgs = localMessages.value.slice()
  if (direction === 'up' && idx > 0) {
    const tmp = msgs[idx - 1]
    msgs[idx - 1] = msgs[idx]
    msgs[idx] = tmp
    localMessages.value = msgs
    ;(emit as any)('reorder', { id: message.id, from: idx, to: idx - 1 })
  } else if (direction === 'down' && idx < msgs.length - 1) {
    const tmp = msgs[idx + 1]
    msgs[idx + 1] = msgs[idx]
    msgs[idx] = tmp
    localMessages.value = msgs
    ;(emit as any)('reorder', { id: message.id, from: idx, to: idx + 1 })
  }
}

// Trigger magic for the message
// Message-level magic modal state and handlers
const showMessageMagicModal = ref(false)
const messageToRefine = ref<ChatMessage | null>(null)

// Options for the three parameters (basic choices provided by UI)
const temperamentOptions = [
  { name: 'Aggressive' },
  { name: 'Exuberant' },
  { name: 'Detached' },
  { name: 'Sarcastic' },
  { name: 'Cynical' },
]
const styleOptions = [
  { name: 'Formal' },
  { name: 'Informal' },
  { name: 'Concise' },
  { name: 'Expressive' },
  { name: 'Neutral' },
]
const lengthOptions = [
  { name: 'Much shorter' },
  { name: 'Slightly shorter' },
  { name: 'Same length' },
  { name: 'Slightly longer' },
  { name: 'Much longer' },
]

const selectedTemperament = ref()
const selectedStyle = ref()
const selectedLength = ref()

// Inputs are editable — users can type custom values directly into the Dropdowns

const openMessageMagicModal = (message: ChatMessage) => {
  messageToRefine.value = message
  // sensible defaults: start empty so user chooses (placeholder will show)
  selectedTemperament.value = null
  selectedStyle.value = null
  selectedLength.value = null
  showMessageMagicModal.value = true
}

const cancelMessageMagic = () => {
  showMessageMagicModal.value = false
  messageToRefine.value = null
  messageMagicPreview.value = null
}

// Confirm: emit an event with chosen params so parent or other handlers can act
const messageMagicLoading = ref(false)
// preview returned by the LLM; if set, show preview and allow keeping/declining
const messageMagicPreview = ref<string | null>(null)

const applyMessageMagic = () => {
  if (!messageToRefine.value || !messageMagicPreview.value) return
  const rewritten = messageMagicPreview.value.trim()
  const idx = localMessages.value.findIndex((m) => m.id === messageToRefine.value!.id)
  if (idx !== -1) {
    localMessages.value[idx] = {
      ...localMessages.value[idx],
      text: rewritten,
    }
  }
  // notify parent so app state / persistence can update
  emit('editMessage', {
    id: messageToRefine.value.id,
    speaker: messageToRefine.value.speaker,
    text: rewritten,
    addressees: messageToRefine.value.addressees || [],
    referenceId: messageToRefine.value.referenceId || undefined,
  })

  // clear preview and close
  messageMagicPreview.value = null
  showMessageMagicModal.value = false
  messageToRefine.value = null
}

const declineMessageMagic = () => {
  // discard preview but keep modal open so user can change parameters or cancel
  messageMagicPreview.value = null
}

const confirmMessageMagic = async () => {
  if (!messageToRefine.value) return
  // Use the current selected/typed values directly (Dropdown is editable)
  const normalizeChoice = (v: any) => {
    if (!v && v !== 0) return ''
    if (typeof v === 'string') return v.trim()
    if (typeof v === 'object' && v !== null) {
      // common pattern: { name: 'Formal' }
      if ('name' in v && typeof v.name === 'string') return v.name.trim()
      // fallback to toString
      try {
        return String(v).trim()
      } catch (e) {
        return ''
      }
    }
    return String(v).trim()
  }

  const temperamentValue = normalizeChoice(selectedTemperament.value)
  const styleValue = normalizeChoice(selectedStyle.value)
  const lengthValue = normalizeChoice(selectedLength.value)

  const apiBase = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

  // prepare payload expected by backend
  const payload: any = {
    // send the single persona object for the speaker (backend expects an object)
    speakerProfile:
      (availablePersonas.value &&
        availablePersonas.value.find((p) => p.name === messageToRefine.value!.speaker)) ||
      undefined,
    messageToRewrite: {
      id: messageToRefine.value.id,
      speaker: messageToRefine.value.speaker,
      text: messageToRefine.value.text,
      addressees: messageToRefine.value.addressees || [],
      referenceId: messageToRefine.value.referenceId || undefined,
    },
    temperament: temperamentValue || undefined,
    style: styleValue || undefined,
    length: lengthValue || undefined,
    // Prefer the local (possibly edited) messages so the rewrite request has
    // the most up-to-date view of the chat (includes manual edits/refinements).
    messagesInTheChat: (localMessages.value || [])
      .filter((m) => messageToRefine.value != null && m.id < messageToRefine.value.id)
      .map((m) => m.text || ''),
  }

  // try to gather tree user messages from loaded file content if possible
  try {
    const speaker = messageToRefine.value.speaker
    if (fileContent.value && fileContent.value.tree) {
      const extracted = getTextsBySpeaker(fileContent.value.tree, speaker)
      if (extracted && extracted.length > 0) payload.treeUserMessages = extracted
    }
  } catch (e) {
    // non-fatal; continue with best-effort context
    console.debug('[TelegramChat] confirmMessageMagic: failed to extract treeUserMessages', e)
  }

  messageMagicLoading.value = true
  try {
    const resp = await fetch(`${apiBase}/api/llm/rewrite-message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!resp.ok) {
      const text = await resp.text()
      throw new Error(text || `HTTP ${resp.status}`)
    }

    const data = await resp.json()
    if (data && data.success && typeof data.rewritten === 'string') {
      const rewritten = data.rewritten.trim()
      // store preview and keep modal open so user can decide to keep or decline
      messageMagicPreview.value = rewritten
    } else {
      throw new Error('Invalid response from server')
    }
  } catch (e: any) {
    console.error('Message rewrite failed', e)
    saveMessage.value = `Rewrite failed: ${e?.message || String(e)}`
    setTimeout(() => (saveMessage.value = ''), 5000)
  } finally {
    messageMagicLoading.value = false
  }
}

// Triggered when the inline magic button is clicked — open modal
const handleMagicForMessage = async (message: ChatMessage) => {
  openMessageMagicModal(message)
}

// Hover state to avoid CSS :hover flakiness. Tracks the message id currently hovered.
const hoveredMessageId = ref<number | null>(null)
// Track active pointer ids per-message so enter/leave pairs are matched reliably.
// Use a Map with Set of pointerIds — we don't need this Map to be reactive because
// rendering depends only on `hoveredMessageId`.
const hoverPointers = new Map<number, Set<number>>()
const debugHoverSnapshot = () =>
  Array.from(hoverPointers.entries()).reduce((acc: Record<string, number>, [k, s]) => {
    acc[String(k)] = s.size
    return acc
  }, {})
const onMessageHover = (id: number, ev?: PointerEvent) => {
  if (!ev) {
    console.debug('[hover] enter (no event)', { id, hoveredMessageId: hoveredMessageId.value })
    return
  }
  const pid = (ev as PointerEvent).pointerId || 0
  // Debug logging to trace pointerenter events during repro. Remove when
  // issue is resolved.
  try {
    console.debug('[hover] enter', {
      id,
      type: ev.type,
      pointerId: pid,
      hoveredMessageId: hoveredMessageId.value,
      pointers: debugHoverSnapshot(),
    })
  } catch (e) {}
  let set = hoverPointers.get(id)
  if (!set) {
    set = new Set<number>()
    hoverPointers.set(id, set)
  }
  set.add(pid)
  hoveredMessageId.value = id
}
const onMessageLeave = (id: number, ev?: PointerEvent) => {
  // Debug logging to trace pointerleave events and relatedTarget.
  try {
    const related = (ev && (ev as any).relatedTarget) as Node | null
    const pid = ev ? (ev as PointerEvent).pointerId || 0 : null
    let relatedMessageId: string | null = null
    if (related && related instanceof HTMLElement)
      relatedMessageId = (related as HTMLElement).dataset.messageId || null
    let pointMessageId: string | null = null
    if (ev && typeof (ev as PointerEvent).clientX === 'number') {
      try {
        const el = document.elementFromPoint(
          (ev as PointerEvent).clientX,
          (ev as PointerEvent).clientY,
        ) as Element | null
        if (el && el instanceof HTMLElement)
          pointMessageId = (el as HTMLElement).dataset.messageId || null
      } catch (e) {
        /* ignore */
      }
    }
    console.debug('[hover] leave', {
      id,
      type: ev?.type,
      pointerId: pid,
      relatedMessageId,
      pointMessageId,
      hoveredMessageId: hoveredMessageId.value,
      pointers: debugHoverSnapshot(),
    })
  } catch (e) {
    console.debug('[hover] leave (logging failed)', { id, err: e })
  }
  // If the pointer moved to another element that's still inside this message
  // (e.g. to the avatar column or the magic button), don't decrement.
  try {
    const related = (ev && (ev as any).relatedTarget) as Node | null
    let stillInside = false

    // First try the relatedTarget ancestry (fast path)
    if (related) {
      let node: Node | null = related
      while (node) {
        if (node instanceof HTMLElement && node.dataset && node.dataset.messageId === String(id)) {
          stillInside = true
          break
        }
        node = node.parentNode
      }
    }

    // If relatedTarget didn't indicate we're still inside, use elementFromPoint
    // as a more reliable fallback to detect the element currently under the pointer.
    if (!stillInside && ev && typeof (ev as PointerEvent).clientX === 'number') {
      try {
        const x = (ev as PointerEvent).clientX
        const y = (ev as PointerEvent).clientY
        const el = document.elementFromPoint(x, y) as Element | null
        let n: Element | null = el
        while (n) {
          if (n instanceof HTMLElement && n.dataset && n.dataset.messageId === String(id)) {
            stillInside = true
            break
          }
          n = n.parentElement
        }
      } catch (e) {
        // ignore; fallback will decrement below
      }
    }

    if (stillInside) {
      // still inside the message subtree — ignore this leave
      return
    }
  } catch (e) {
    // defensive: if anything goes wrong, fall back to normal behavior
  }

  // Use pointerId to decrement the appropriate entry. If ev is missing, try
  // to be conservative and clear the set for this id.
  try {
    if (!ev) {
      hoverPointers.delete(id)
      if (hoveredMessageId.value === id) hoveredMessageId.value = null
      return
    }
    const pid = (ev as PointerEvent).pointerId || 0
    const set = hoverPointers.get(id)
    if (!set) {
      // No pointer set recorded for this message — fall back to clearing
      // hoveredMessageId to avoid leaving the controls visible.
      hoverPointers.delete(id)
      if (hoveredMessageId.value === id) {
        console.debug('[hover] leave fallback: clearing hoveredMessageId (no set)', { id, pid })
        hoveredMessageId.value = null
      }
      return
    }
    set.delete(pid)
    if (set.size === 0) {
      hoverPointers.delete(id)
      if (hoveredMessageId.value === id) hoveredMessageId.value = null
    }
  } catch (e) {
    // fallback: clear
    hoverPointers.delete(id)
    if (hoveredMessageId.value === id) hoveredMessageId.value = null
  }
}

// Robust fallback hover tracking: listen to pointermove on the messages container
// and update `hoveredMessageId` based on elementFromPoint. This avoids enter/leave
// pairing races when the pointer moves quickly between message bubbles.
let pointerMovePending = false
const pointerMoveHandler = (ev: PointerEvent) => {
  if (pointerMovePending) return
  pointerMovePending = true
  const x = ev.clientX
  const y = ev.clientY
  requestAnimationFrame(() => {
    pointerMovePending = false
    try {
      const el = document.elementFromPoint(x, y) as Element | null
      let mid: number | null = null
      let elInfo: any = null
      let n: Element | null = el
      while (n) {
        if (n instanceof HTMLElement && n.dataset && n.dataset.messageId) {
          const parsed = Number(n.dataset.messageId)
          if (!Number.isNaN(parsed)) mid = parsed
          break
        }
        n = n.parentElement
      }
      try {
        elInfo = el
          ? {
              tag: (el as HTMLElement).tagName,
              id: (el as HTMLElement).id || null,
              dataset: (el as HTMLElement).dataset?.messageId || null,
            }
          : null
      } catch (e) {
        elInfo = null
      }
      if (mid !== hoveredMessageId.value) {
        console.debug(
          '[pointerMove] coords',
          { x, y },
          'elementFromPoint',
          elInfo,
          'oldHovered',
          hoveredMessageId.value,
          'newMid',
          mid,
        )
        // Clear any stale pointer tracking for messages — pointermove is authoritative.
        try {
          hoverPointers.clear()
        } catch (e) {
          /* ignore */
        }
        hoveredMessageId.value = mid
      }
    } catch (e) {
      // ignore
    }
  })
}

const onMessagesContainerPointerLeave = () => {
  hoveredMessageId.value = null
}

onMounted(() => {
  // attach pointermove to the container for robust hover detection
  nextTick(() => {
    const el = messagesContainer.value as HTMLElement | undefined
    if (el && typeof el.addEventListener === 'function') {
      el.addEventListener('pointermove', pointerMoveHandler)
      el.addEventListener('pointerleave', onMessagesContainerPointerLeave)
    }
  })
})

onBeforeUnmount(() => {
  const el = messagesContainer.value as HTMLElement | undefined
  if (el && typeof el.removeEventListener === 'function') {
    el.removeEventListener('pointermove', pointerMoveHandler)
    el.removeEventListener('pointerleave', onMessagesContainerPointerLeave)
  }
})

// Auto-scroll when new messages are added
watch(
  () => localMessages.value.length,
  () => {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  },
)

// Expose methods to set speaker and addressees from parent
defineExpose({
  setSpeaker: (speaker: string) => {
    selectedSpeaker.value = speaker
  },
  setAddressees: (addrs: string[]) => {
    selectedAddressees.value = Array.isArray(addrs) ? addrs : []
    // also emit to parent so any listeners are updated
    ;(emit as any)('update:addressees', selectedAddressees.value)
  },
  setReferenceId: (refId: string | null) => {
    selectedReferenceId.value = refId
  },
})
</script>

<style scoped>
/* Settings Modal Styles */
.settings-modal-body {
  padding: 10px 0;
}
.settings-modal-body h4 {
  margin-bottom: 12px;
  font-size: 18px;
  color: #0088cc;
}
.users-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.user-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}
.user-avatar {
  /* Force a fixed square box so border-radius:50% reliably makes a circle
     even if parent layout changes or padding/box-sizing differ. */

  min-width: 32px;
  min-height: 32px;
  max-width: 32px;
  max-height: 32px;
  flex: 0 0 32px; /* prevent flex item from growing/shrinking */
  background: #0088cc;
  color: #fff;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 18px;
  margin-right: 12px;
  overflow: hidden; /* clip any children/content that might overflow */
  box-sizing: border-box;
}
.user-name {
  font-size: 16px;
  color: #333;
}
/* spacing: ensure there's comfortable gap between name and the input row */
.user-name {
  margin-right: 12px;
}

.user-description-input {
  font-size: 14px;
  color: #333;
  border: 1px solid #e6eef4;
  background: #fff;
  padding: 6px 8px;
  border-radius: 6px;
  margin-left: 12px;
  min-width: 180px;
  width: 100%;
  min-height: 40px; /* allow multiple lines */
  line-height: 1.3;
  resize: vertical; /* let users expand if they want */
  max-height: 220px;
  overflow: auto;
}

.user-input-row {
  display: flex;
  gap: 8px;
  align-items: center; /* center button vertically relative to textarea */
  width: 100%;
}

.user-input-row .user-description-input {
  /* remove the left margin inside the input row; spacing is handled by gap */
  margin-left: 0;
}

.magic-btn {
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  border-radius: 50%;
  background: #ffb74d;
  color: #fff;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.magic-btn[disabled] {
  opacity: 0.6;
  cursor: progress;
}

.magic-btn svg {
  width: 18px;
  height: 18px;
}

.magic-loading {
  font-size: 18px;
  line-height: 1;
}
.user-description-input:focus {
  outline: none;
  border-color: #0088cc;
  box-shadow: 0 0 0 3px rgba(0, 136, 204, 0.08);
}
.debug-json {
  background: #f7f9fb;
  border: 1px solid #e6eef4;
  padding: 10px;
  border-radius: 6px;
  font-size: 12px;
  color: #223;
  max-height: 220px;
  overflow: auto;
  white-space: pre-wrap;
}
/* Draft name input */
.draft-name-input {
  width: 100%;
  padding: 8px 10px;
  margin: 6px 0 12px 0;
  border-radius: 6px;
  border: 1px solid #e6eef4;
  font-size: 14px;
}
/* Footer inside settings modal */
.settings-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}
.save-btn {
  background-color: #006ba3;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 700;
}
.save-btn[disabled],
.save-btn[aria-disabled='true'] {
  background-color: #c9dbe6;
  cursor: not-allowed;
  color: #fff;
}
.save-message {
  color: #2b8a3e;
  font-weight: 600;
  margin-left: 8px;
}
/* Settings button styles */
.settings-button {
  background: none;
  border: none;
  color: #fff;
  margin-left: 12px;
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  transition: background 0.2s;
  display: flex;
  align-items: center;
}
.settings-button:hover {
  background: rgba(255, 255, 255, 0.12);
}
.chat-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #ffffff; /* card background */
  color: #222;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

/* Ensure the chat card can shrink properly inside flex containers */
.chat-section {
  min-height: 0;
  height: 100%;
}

.chat-header {
  padding: 12px 16px;
  background-color: #006ba3; /* keep the blue header accent */
  color: #fff;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}

.chat-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  background-color: #ffffff;
}

.message {
  margin-bottom: 15px;
  cursor: text;
  animation: slideIn 0.3s ease-out;
}

.message {
  position: relative;
}

.editing-message {
  box-shadow: 0 0 0 3px rgba(0, 136, 204, 0.08);
  border-radius: 12px;
  padding: 6px;
}

.message.own-message {
  text-align: right;
}

.message.own-message .message-text {
  background-color: #e6f4ea; /* softer green bubble for own messages */
  color: #0b6623;
  margin-left: auto;
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
  font-size: 11px;
  opacity: 0.8;
}

.message-body {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
}

.arrow-controls {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 6px;
  align-items: center;
  opacity: 0;
  visibility: hidden;
  transition:
    opacity 0.12s ease-in-out,
    transform 0.12s ease-in-out;
}
.message.hovered .avatar-column .arrow-controls {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}
.arrow-btn {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.06);
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #333;
}
.arrow-btn:hover {
  background: rgba(0, 0, 0, 0.1);
}

/* Magic / sparkles button inside message bubble */
.message-text {
  position: relative;
}
.message-magic-btn {
  position: absolute;
  right: 6px;
  top: 6px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #ffb74d;
  color: #fff;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
  padding: 0;
  opacity: 0;
  visibility: hidden;
  transition:
    opacity 0.12s ease-in-out,
    transform 0.12s ease-in-out;
}
.message-magic-btn svg {
  width: 14px;
  height: 14px;
}
.message-magic-btn:hover {
  filter: brightness(0.95);
}

.message.hovered .message-magic-btn {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

.avatar-column {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-right: 10px;
}

.message.own-message .message-header {
  flex-direction: row-reverse;
}

.speaker {
  font-weight: 600;
}

.addressees {
  color: #6c757d; /* muted dark color for visibility on light background */
  font-style: italic;
  font-size: 12px;
  margin-left: 0;
}

.addressee-chip {
  display: inline-block;
  padding: 2px 6px;
  margin-left: 6px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid transparent;
}

.message-meta {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}

.turn {
  font-size: 10px;
}

.message-text {
  background-color: #f5f7fa; /* neutral bubble for incoming messages */
  padding: 8px 12px;
  border-radius: 16px;
  display: inline-block;
  max-width: 80%;
  word-wrap: break-word;
  font-size: 14px;
  line-height: 1.4;
  color: #111;
}

.chat-input {
  padding: 12px 12px;
  background-color: #fbfdff; /* subtle light footer */
  display: flex;
  gap: 10px;
  align-items: center;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
}

.cancel-edit-btn {
  background: none;
  border: 1px solid #c9dbe6;
  color: #006ba3;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.cancel-edit-btn:hover {
  background: #f3f8fb;
}

.speaker-chip {
  display: flex;
  align-items: center;
  background: #ffffff;
  color: #0088cc;
  border-radius: 16px;
  padding: 4px 12px;
  margin-right: 8px;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}
.remove-chip {
  background: none;
  border: none;
  color: #0088cc;
  font-size: 18px;
  margin-left: 6px;
  cursor: pointer;
}

.speaker-select-dropdown {
  position: relative;
}
.speaker-select-btn {
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 20px;
  padding: 10px 20px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s;
}
.speaker-select-btn:hover {
  background-color: #45a049;
}
.dropdown-content {
  position: absolute;
  top: 110%;
  left: 0;
  background: #fff;
  color: #0088cc;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  min-width: 120px;
  z-index: 10;
  display: flex;
  flex-direction: column;
}
.dropdown-item {
  background: none;
  border: none;
  padding: 10px 16px;
  text-align: left;
  cursor: pointer;
  font-weight: 600;
  color: #0088cc;
}
.dropdown-item:hover {
  background: #e0f7fa;
}
.message-input::placeholder {
  color: rgba(255, 255, 255, 0.6);
}

.message-input:focus {
  outline: none;
  background-color: rgba(255, 255, 255, 0.2);
}

.send-button {
  padding: 10px 20px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s;
}

.send-button:hover {
  background-color: #45a049;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Responsive design */
@media (max-width: 768px) {
  .chat-section {
    flex: 1;
  }
}

/* Message Magic Modal - additional styling to match the provided design */
.settings-modal-body .debug-json pre {
  background: #f5f8fa;
  border-radius: 8px;
  padding: 14px;
  color: #333;
  margin: 0 0 12px 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, 'Roboto Mono', monospace;
}

.magic-params-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 12px 0;
}

.magic-params-row label {
  min-width: 110px;
  color: #222;
  font-weight: 600;
}

.magic-params-row select {
  appearance: none;
  -webkit-appearance: none;
  border: none;
  background: #f0f3f5;
  padding: 6px 12px;
  border-radius: 14px;
  box-shadow: inset 0 0 0 1px rgba(16, 24, 32, 0.04);
  font-size: 13px;
  color: #111827;
}

.custom-text-input {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #e6eef4;
  background: #fff;
  min-width: 240px;
  width: 100%;
}

.custom-input-row label {
  min-width: 110px;
}

.settings-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  align-items: center;
}

.settings-footer .save-btn {
  background: #0077b6;
  color: white;
  border: none;
  padding: 10px 18px;
  border-radius: 8px;
  cursor: pointer;
}

.settings-footer .save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.settings-footer .magic-btn {
  background: #ffb03b;
  color: white;
  border: none;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
  cursor: pointer;
}

@media (max-width: 700px) {
  .magic-params-row {
    flex-direction: column;
    align-items: flex-start;
  }
  .magic-params-row label {
    min-width: auto;
  }
}
</style>
