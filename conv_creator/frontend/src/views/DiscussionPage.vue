<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DiscussionGraph from '../components/graph/DiscussionGraph.vue'
import TelegramChat from '../components/chat/TelegramChat.vue'
import FileSelectorModal from '../components/shared/FileSelectorModal.vue'
import { useUsers } from '../composables/useUsers'

interface ChatMessage {
  id: number
  sender: string
  text: string
  time: string
}

const { getThesisStatement, getRandomPersona, loadUsers } = useUsers()

// Initialize messages empty; we'll populate after loading personas so we have a valid thesis author
const messages = ref<ChatMessage[]>([])
const thesisAuthor = ref<{ name: string }>({ name: 'Thesis' })

// Router/route and modal state
const route = useRoute()
const router = useRouter()
const showFileSelector = ref(false)

// Load personas from backend and create the initial thesis message
onMounted(async () => {
  try {
    await loadUsers()
  } catch (e) {
    // loadUsers already logs errors; continue with fallback
  }

  thesisAuthor.value = getRandomPersona() || { name: 'Thesis' }
  messages.value.push({
    id: 1,
    sender: thesisAuthor.value.name,
    text: getThesisStatement(),
    time: new Date(Date.now() - 120000).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }),
  })

  // Show selector if no file query
  const fname = route.query.file as string | undefined
  if (!fname) showFileSelector.value = true
})

const chatInputValue = ref('')

const handleSendMessage = (message: { sender: string; text: string; time: string }) => {
  messages.value.push({
    id: messages.value.length + 1,
    ...message,
  })
}

const handleUpdateInput = (value: string) => {
  chatInputValue.value = value
}

const telegramChatRef = ref()
const handleAddFromGraph = (messageData: {
  text: string
  type: 'user' | 'bot'
  nodeId: string
  nodeType: string
}) => {
  chatInputValue.value = messageData.text
  // Set the sender in the chat input (default to thesis author)
  if (telegramChatRef.value && telegramChatRef.value.setSender) {
    telegramChatRef.value.setSender(thesisAuthor.value.name)
  }
}

// Collapse state for left graph panel
const graphCollapsed = ref(false)
const toggleGraphCollapsed = () => {
  graphCollapsed.value = !graphCollapsed.value
}
</script>

<template>
  <div class="discussion-page">
    <!-- Navigation Header -->
    <div class="nav-header">
      <router-link to="/" class="back-button"> ← Back to Home </router-link>
      <h1 class="page-title">Discussion Interface</h1>
      <button class="open-file-button" @click="showFileSelector = true">Choose file</button>
      <!-- Collapse toggle placed in the header for quick access -->
      <button
        class="collapse-header-button"
        @click="toggleGraphCollapsed"
        :aria-pressed="graphCollapsed"
        :title="graphCollapsed ? 'Open graph' : 'Collapse graph'"
      >
        <span v-if="!graphCollapsed">◀</span>
        <span v-else>▶</span>
      </button>
      <div class="nav-spacer"></div>
    </div>

    <!-- Main Discussion Container -->
    <div class="discussion-container">
      <!-- Left side - Graph representation (collapsible) -->
      <div :class="['graph-wrapper', { collapsed: graphCollapsed }]">
        <button
          class="collapse-toggle"
          @click="toggleGraphCollapsed"
          :aria-pressed="graphCollapsed"
        >
          <span v-if="!graphCollapsed">◀</span>
          <span v-else>▶</span>
        </button>
        <DiscussionGraph @add-message="handleAddFromGraph" />
      </div>

      <!-- Right side - Telegram chat simulation (1/4 width) -->
      <div class="chat-wrapper" :class="{ expanded: graphCollapsed }">
        <TelegramChat
          ref="telegramChatRef"
          :messages="messages"
          :input-value="chatInputValue"
          @send-message="handleSendMessage"
          @update-input="handleUpdateInput"
          title="Discussion Chat"
          status="Online"
          current-user="You"
          input-placeholder="Type a message..."
        />
      </div>
    </div>

    <FileSelectorModal
      v-if="showFileSelector"
      @select="
        (name) => {
          showFileSelector = false
          router.push({ path: '/discussion', query: { file: name } })
        }
      "
      @close="() => (showFileSelector = false)"
    />
  </div>
</template>

<style scoped>
.discussion-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.nav-header {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  min-height: 60px;
  box-sizing: border-box;
}

.back-button {
  color: #6c757d;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.back-button:hover {
  background: #e9ecef;
  color: #495057;
}

.page-title {
  flex: 1;
  text-align: center;
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #495057;
}

.nav-spacer {
  width: 120px; /* Same width as back button to center the title */
}

.discussion-container {
  display: flex;
  flex: 1;
  min-height: 0; /* Allow flex children to shrink */
}

/* Give the graph section flexible width */
.discussion-container > :first-child {
  flex: 1;
  min-width: 0; /* Allow shrinking below content width */
  overflow: hidden; /* Prevent content from breaking layout */
}

.discussion-container > .chat-wrapper,
.discussion-container > :last-child {
  flex: 0 0 320px; /* Fixed width for chat, but allow it to shrink on very small screens */
  min-width: 280px;
}

.chat-wrapper {
  display: flex;
  min-width: 0;
}

.chat-wrapper.expanded {
  flex: 1 1 auto !important; /* force the chat to grow when graph is collapsed */
  min-width: 0 !important;
  width: auto !important;
}

/* Extra safety: when collapsed, make the chat occupy remaining space explicitly */
.discussion-container .chat-wrapper.expanded {
  flex-basis: 0 !important;
}

/* Wrapper for the left graph section so it can be collapsed */
.graph-wrapper {
  position: relative;
  display: flex;
  flex: 1;
  min-width: 0;
  transition:
    width 220ms ease,
    margin 220ms ease;
  overflow: hidden;
}

.graph-wrapper.collapsed {
  width: 0;
  min-width: 0;
  margin-right: 0;
  flex: 0 0 0; /* collapse to zero space */
  padding: 0;
}

/* Hide the graph content when collapsed but keep the toggle visible */
.graph-wrapper.collapsed > * {
  /* keep component mounted but hidden */
  display: none;
}

.collapse-toggle {
  position: absolute;
  left: 0;
  top: 12px;
  z-index: 40;
  width: 36px;
  height: 36px;
  border-radius: 6px;
  border: 1px solid #e3e6ea;
  background: #ffffffcc;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.graph-wrapper.collapsed .collapse-toggle {
  left: 4px;
}

.graph-wrapper .collapse-toggle:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(100, 150, 250, 0.12);
}

/* Hide the original in-graph toggle since we have a header button now */
.graph-wrapper .collapse-toggle {
  display: none;
}

.collapse-header-button {
  margin-left: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid #dfe4e8;
  background: white;
  cursor: pointer;
  color: #343a40;
  font-weight: 600;
}

.collapse-header-button:hover {
  background: #f1f5f8;
}

/* Responsive design */
@media (max-width: 1200px) {
  .discussion-container > :last-child {
    flex: 0 0 280px;
  }
}

@media (max-width: 768px) {
  .nav-header {
    padding: 0.75rem 1rem;
  }

  .page-title {
    font-size: 1.1rem;
  }

  .discussion-container {
    flex-direction: column;
  }

  .discussion-container > :first-child {
    flex: 1;
    min-height: 60vh;
  }

  .discussion-container > :last-child {
    flex: 0 0 40vh;
    min-width: auto;
  }
}

@media (max-width: 480px) {
  .nav-header {
    padding: 0.5rem;
  }

  .back-button {
    padding: 0.5rem;
    font-size: 0.9rem;
  }

  .page-title {
    font-size: 1rem;
  }

  .nav-spacer {
    width: 80px;
  }

  .discussion-container > :first-child {
    min-height: 50vh;
  }

  .discussion-container > :last-child {
    flex: 0 0 50vh;
  }
}
</style>
