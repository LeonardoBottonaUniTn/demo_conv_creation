<template>
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
        v-for="(message, index) in messages"
        :key="message.id"
        class="message"
        :class="{ 'own-message': message.sender === currentUser }"
      >
        <div class="message-header">
          <span class="sender">
            {{ message.sender }}
            <span v-if="message.addressees && message.addressees.length > 0" class="addressees">
              → {{ message.addressees.join(', ') }}
            </span>
          </span>
          <span class="time">Turn {{ index + 1 }}</span>
        </div>
        <div class="message-text">{{ message.text }}</div>
      </div>
    </div>

    <div class="chat-input">
      <ChatInput
        v-model="newMessage"
        :placeholder="inputPlaceholder"
        style="flex: 1"
        @send="sendMessage"
        @update:sender="selectSender"
        @update:addressees="selectAddressees"
        @update:modelValue="handleInputUpdate"
      />
    </div>

    <!-- Settings Modal -->
    <Modal :isVisible="showSettingsModal" title="Group Description" @close="closeSettings">
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

//TODO: integrate with real backend LLM call if desired
// Per-user generation (magic) state and handler
const generatingUsers = reactive<Record<string, boolean>>({})

const handleMagic = async (name: string) => {
  // Real LLM-backed autofill: if the user has >=4 chat messages, send those as context;
  // otherwise fetch the discussion file and extract all tree nodes authored by the user.
  generatingUsers[name] = true
  try {
    const apiBase = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

    // Gather messages from the chat view
    const userMsgs = props.messages.filter((m) => m.sender === name).map((m) => ({ text: m.text, time: (m as any).time }))

    const payload: any = { name }

    if (userMsgs.length >= 4) {
      // pass the user's most recent messages (up to last 4)
      payload.messages = userMsgs.slice(-4)
    } else {
      // need tree nodes: fetch discussion file and extract nodes authored by this user
      const target = (route?.query?.file as string)
      if (!target) {
        // Do not fallback to a bundled reference file — require an explicit discussion file
        throw new Error('No discussion file specified in route query; cannot fetch nodes.')
      }
      const fileRes = await fetch(`${apiBase}/api/files/${target}`)
      if (!fileRes.ok) {
        const text = await fileRes.text()
        throw new Error(text || `Failed to fetch discussion file: ${fileRes.status}`)
      }
      const fileData = await fileRes.json()

      // traverse tree and collect nodes where speaker === name
      const nodes: Array<Record<string, any>> = []
      const walk = (node: any) => {
        if (!node) return
        if (node.speaker === name) nodes.push({ id: node.id, text: node.text })
        if (Array.isArray(node.children)) node.children.forEach(walk)
      }

      // Support different file shapes: top-level 'tree' or direct root node
      if (fileData && fileData.tree) {
        walk(fileData.tree)
      } else if (Array.isArray(fileData)) {
        fileData.forEach(walk)
      } else if (typeof fileData === 'object') {
        // try to locate a likely root
        if (fileData.root) walk(fileData.root)
        else if (fileData.id && fileData.speaker) walk(fileData)
      }

      payload.nodes = nodes
    }

    // Call backend LLM endpoint to generate a description
    const genRes = await fetch(`${apiBase}/api/llm/generate_description`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!genRes.ok) {
      const text = await genRes.text()
      throw new Error(text || `LLM generate failed: ${genRes.status}`)
    }
    const data = await genRes.json()
    const generated = data.description || `Auto-generated description for ${name}`
    descriptions[name] = generated
    updateDescription(name)
  } catch (e) {
    console.error('Magic generation failed for', name, e)
    // fallback: keep UI reactive, optionally set a user-visible error later
  } finally {
    generatingUsers[name] = false
  }
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

  saveMessage.value = 'Saving...'
  try {
    // include target when available (current discussion file from route query)
    const target = (route?.query?.file as string) || undefined
    const payload: any = { users: usersToSend }
    if (target) payload.target = target

    const res = await fetch(`${apiBase}/api/files/${target}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const text = await res.text()
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
  currentUser?: string
  inputPlaceholder?: string
  inputValue?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Discussion Chat',
  currentUser: 'You',
  inputPlaceholder: 'Type a message...',
  inputValue: '',
})

const emit = defineEmits<{
  sendMessage: [message: { sender: string; text: string; time: string; addressees?: string[] }]
  updateInput: [value: string]
}>()

const newMessage = ref('')
const messagesContainer = ref<HTMLElement>()
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
  loadUsers()
    .then(() => {
      populateDescriptions()
    })
    .catch((e) => console.warn('Failed to load personas for settings modal:', e))
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
  const message = {
    sender: selectedSender.value,
    text: newMessage.value,
    time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    addressees: selectedAddressees.value,
  }
  emit('sendMessage', message)
  newMessage.value = ''
  emit('updateInput', '') // Emit the update to parent
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

// Auto-scroll when new messages are added
watch(
  () => props.messages.length,
  () => {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  },
)

// Expose a method to set the sender from parent (App.vue)
defineExpose({
  setSender: (sender: string) => {
    selectedSender.value = sender
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
  animation: slideIn 0.3s ease-out;
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
  color: rgba(255, 255, 255, 0.7);
  font-style: italic;
  font-size: 10px;
  margin: 0 5px;
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
