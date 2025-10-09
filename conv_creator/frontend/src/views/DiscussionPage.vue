<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DiscussionGraph from '../components/graph/DiscussionGraph.vue'
import TelegramChat from '../components/chat/TelegramChat.vue'
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
</script>

<template>
  <div class="discussion-page">
    <!-- Navigation Header -->
    <div class="nav-header">
      <router-link to="/" class="back-button"> ← Back to Home </router-link>
      <h1 class="page-title">Discussion Interface</h1>
      <div class="nav-spacer"></div>
    </div>

    <!-- Main Discussion Container -->
    <div class="discussion-container">
      <!-- Left side - Graph representation (3/4 width) -->
      <DiscussionGraph @add-message="handleAddFromGraph" />

      <!-- Right side - Telegram chat simulation (1/4 width) -->
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

.discussion-container > :last-child {
  flex: 0 0 320px; /* Fixed width for chat, but allow it to shrink on very small screens */
  min-width: 280px;
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
