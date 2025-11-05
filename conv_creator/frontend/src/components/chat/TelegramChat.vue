<template>
  <!-- TODO: fix line 29-->
  <div class="chat-section">
    <div class="chat-header">
      <h3>{{ title }}</h3>
      <button class="settings-button" @click="openSettings" title="Settings">
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="3" />
          <path
            d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.09A1.65 1.65 0 0 0 11 3.09V3a2 2 0 1 1 4 0v.09c0 .66.39 1.26 1 1.51a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.09c.66.39 1.26 1.09 1.51 1.82H21a2 2 0 1 1 0 4h-.09c-.22.63-.82 1.23-1.51 1.51z"
          />
        </svg>
      </button>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="(message, index) in localMessages"
        :key="message.id"
        class="message"
        :class="{
          'own-message': message.sender === selectedSender,
          'editing-message': message.id === editingMessageId,
        }"
        @dblclick.prevent="editMessage(message, index)"
      >
        <div class="message-header">
          <div class="message-meta">
            <span class="sender">{{ message.sender }}</span>
            <span v-if="message.addressees && message.addressees.length > 0" class="addressees"
              >→ {{ message.addressees.join(', ') }}</span
            >
          </div>
          <span class="time">Turn {{ index + 1 }}</span>
        </div>
        <div class="message-text">{{ message.text }}</div>
      </div>
    </div>

    <div class="chat-input">
      <ChatInput
        ref="chatInputRef"
        v-model="newMessage"
        :placeholder="inputPlaceholder"
        :selected-sender="selectedSender"
        :selected-addressees="selectedAddressees"
        style="flex: 1"
        @send="sendMessage"
        @update:sender="selectSender"
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
            <span class="user-avatar">{{ user.charAt(0).toUpperCase() }}</span>
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
                @click="handleMagic(user)"
                :disabled="generatingUsers[user]"
                :title="`Magic fill for ${user}`"
                aria-label="Magic autofill description"
              >
                <template v-if="!generatingUsers[user]">
                  <!-- Inline magic-wand SVG to avoid external dependency -->
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M22 2l-6 6" />
                    <path d="M16 8l-10 10" />
                    <path d="M7 7l-1.5 1.5" />
                    <path d="M3 13l1.5 1.5" />
                    <circle cx="19" cy="5" r="1" />
                  </svg>
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
            @click="handleSave"
            :title="isDirtyAny ? 'Save changes' : 'No changes to save'"
          >
            Save
          </button>

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

const showSettingsModal = ref(false)
const openSettings = () => {
  console.debug('[TelegramChat] openSettings called')
  showSettingsModal.value = true
}
const closeSettings = () => {
  showSettingsModal.value = false
}

// Load personas from backend so settings modal can show them
const { loadUsers, personas, availablePersonas, currentPersona } = useUsers()

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
  const users = props.messages.map((m) => m.sender)
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
  const users = Array.from(new Set(props.messages.map((m) => m.sender)))
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
  let context: string[] = props.messages.filter((m) => m.sender === name).map((m) => m.text)
  console.log('Initial context from messages (length):', context.length)
  // If the immediate messages are too short, try to fetch the discussion file and extract more nodes
  console.log('Condition to go to try catch', context.length < 4)
  if (context.length < 4) {
    try {
      console.log('So try to get from debate tree')
      const target = activeFile.value
      const apiBase = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'
      if (target) {
        const res = await fetch(`${apiBase}/api/files/${target}`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        })
        console.log(
          'Fetching additional context for user',
          name,
          'from file',
          target,
          'Response:',
          res,
        )
        if (res.ok) {
          const fileData = await res.json()
          // extract all nodes by this user from the discussion tree
          const extracted = getTextsBySpeaker(fileData.tree, name)
          console.log('context type', typeof extracted)
          console.log('context content', extracted)
          if (extracted && extracted.length > 0) context = extracted
          return context
        }
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

const handleMagic = async (name: string) => {
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
const handleSave = async () => {
  // prepare payload: use availablePersonas if present (they track ids), otherwise use personas
  const apiBase = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'
  const usersToSend = (
    availablePersonas.value && availablePersonas.value.length > 0
      ? availablePersonas.value
      : personas.value
  ).map((p: any) => {
    // backend expects a 'speaker' field historically; include description too
    return {
      speaker: p.name || p.speaker,
      description: p.description || descriptions[p.name || p.speaker] || '',
    }
  })
  // include target when available (prefer prop, then params, then query)
  const target = activeFile.value
  if (!target) {
    saveMessage.value = 'Cannot save: no active discussion file selected.'
    setTimeout(() => (saveMessage.value = ''), 4000)
    return
  }

  saveMessage.value = 'Saving...'
  try {
    const payload: any = { users: usersToSend }

    // normalize target: backend expects a path relative to files_root (no leading 'files_root/')
    let normalizedTarget = String(target || '')
    if (normalizedTarget.startsWith('files_root/')) {
      normalizedTarget = normalizedTarget.substring('files_root/'.length)
    }
    if (normalizedTarget.startsWith('/')) normalizedTarget = normalizedTarget.substring(1)

    const url = `${apiBase}/api/files/${encodeURIComponent(normalizedTarget)}`
    console.debug('[TelegramChat] Saving users', { url, payload, normalizedTarget })
    const res = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const text = await res.text()
      console.error('[TelegramChat] Save failed response', res.status, text)
      throw new Error(text || `HTTP ${res.status}`)
    }
    // success: update original snapshot and show confirmation
    Object.keys(descriptions).forEach((k) => {
      originalDescriptions[k] = descriptions[k] || ''
    })
    saveMessage.value = 'Saved'
    setTimeout(() => (saveMessage.value = ''), 1600)
    // close modal after saving
    closeSettings()
  } catch (err: any) {
    console.error('Failed to save users:', err)
    saveMessage.value = `Save failed: ${err?.message || String(err)}`
    // clear message after a little while but keep modal open so user can retry
    setTimeout(() => (saveMessage.value = ''), 5000)
  }
}

// Keyboard shortcut and navigation protection when settings modal is open
const onKeyDown = (e: KeyboardEvent) => {
  const key = e.key ? e.key.toLowerCase() : ''
  if ((e.ctrlKey || e.metaKey) && key === 's') {
    e.preventDefault()
    if (isDirtyAny.value) handleSave()
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
  sender: string
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

// Active file: prefer explicit prop from parent, fall back to router params/query
const activeFile = computed(() => {
  const p = (props as any).file as string | undefined
  const param = (route?.params?.file as string) || undefined
  const query = (route?.query?.file as string) || undefined
  return p || param || query || undefined
})

const emit = defineEmits<{
  sendMessage: [message: { sender: string; text: string; time: string; addressees?: string[] }]
  editMessage: [
    message: { id: number; sender: string; text: string; time: string; addressees?: string[] },
  ]
  updateInput: [value: string]
  'update:sender': [sender: string]
  'update:addressees': [addressees: string[]]
}>()

const newMessage = ref('')
const messagesContainer = ref<HTMLElement>()
const editingMessageId = ref<number | null>(null)
const chatInputRef = ref<any>(null)
const possibleSenders = ref(['You', 'Bot', 'Admin'])
const selectedSender = ref<string | null>(null)
const selectedAddressees = ref<string[]>([])

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
  console.debug('[TelegramChat] onMounted: loading users for active file', activeFile.value)
  if (activeFile.value) {
    loadUsers(activeFile.value)
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
  if (!selectedSender.value || !newMessage.value.trim() || selectedAddressees.value.length === 0) {
    // Do nothing, sender must be selected, message not empty, and at least one addressee selected
    return
  }

  const payloadBase = {
    sender: selectedSender.value,
    text: newMessage.value,
    time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    addressees: selectedAddressees.value,
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

const selectSender = (sender: string) => {
  selectedSender.value = sender
}

const selectAddressees = (addressees: string[]) => {
  selectedAddressees.value = addressees
}

const handleInputUpdate = (value: string) => {
  newMessage.value = value
  emit('updateInput', value)
}

const removeSender = () => {
  selectedSender.value = null
}

const cancelEdit = () => {
  // clear editing state and notify parent/components
  editingMessageId.value = null
  newMessage.value = ''
  selectedSender.value = null
  selectedAddressees.value = []
  ;(emit as any)('update:sender', selectedSender.value)
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
 * The message stays in the chat; this just populates the input + sender/addressees.
 */
const editMessage = async (message: ChatMessage, _index: number) => {
  // mark which message we are editing so sendMessage can emit editMessage
  editingMessageId.value = message.id
  selectedSender.value = message.sender
  selectedAddressees.value = Array.isArray(message.addressees) ? [...message.addressees] : []
  newMessage.value = message.text || ''

  // notify parent/listeners about the selection change and input update
  ;(emit as any)('update:sender', selectedSender.value)
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

// Expose methods to set sender and addressees from parent
defineExpose({
  setSender: (sender: string) => {
    selectedSender.value = sender
  },
  setAddressees: (addrs: string[]) => {
    selectedAddressees.value = Array.isArray(addrs) ? addrs : []
    // also emit to parent so any listeners are updated
    ;(emit as any)('update:addressees', selectedAddressees.value)
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

.message.own-message .message-header {
  flex-direction: row-reverse;
}

.sender {
  font-weight: 600;
}

.addressees {
  color: #6c757d; /* muted dark color for visibility on light background */
  font-style: italic;
  font-size: 12px;
  margin-left: 0;
}

.message-meta {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}

.time {
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

.sender-chip {
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

.sender-select-dropdown {
  position: relative;
}
.sender-select-btn {
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 20px;
  padding: 10px 20px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s;
}
.sender-select-btn:hover {
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
</style>
