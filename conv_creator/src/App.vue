<script setup lang="ts">
import { ref } from 'vue'
import DiscussionGraph from './components/graph/DiscussionGraph.vue'
import TelegramChat from './components/chat/TelegramChat.vue'
import { useUsers } from './composables/useUsers'

interface ChatMessage {
  id: number
  sender: string
  text: string
  time: string
}

const { getThesisStatement, getRandomPersona } = useUsers()

// Initialize messages with the thesis statement as the first message
const thesisAuthor = getRandomPersona()
const messages = ref<ChatMessage[]>([
  {
    id: 1,
    sender: thesisAuthor.name,
    text: getThesisStatement(),
    time: new Date(Date.now() - 120000).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }),
  },
])

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

const handleAddFromGraph = (messageData: {
  text: string
  type: 'user' | 'bot'
  nodeId: string
  nodeType: string
}) => {
  // Instead of adding directly to chat, populate the input field without prefix
  chatInputValue.value = messageData.text
}
</script>

<template>
  <div class="app-container">
    <!-- Left side - Graph representation (3/4 width) -->
    <DiscussionGraph @add-message="handleAddFromGraph" />

    <!-- Right side - Telegram chat simulation (1/4 width) -->
    <TelegramChat
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
</template>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  min-height: 0; /* Allow flex children to shrink */
}

/* Give the graph section flexible width */
.app-container > :first-child {
  flex: 1;
  min-width: 0; /* Allow shrinking below content width */
  overflow: hidden; /* Prevent content from breaking layout */
}

.app-container > :last-child {
  flex: 0 0 320px; /* Fixed width for chat, but allow it to shrink on very small screens */
  min-width: 280px;
}

/* Responsive design */
@media (max-width: 1200px) {
  .app-container > :last-child {
    flex: 0 0 280px;
  }
}

@media (max-width: 768px) {
  .app-container {
    flex-direction: column;
    height: auto;
    min-height: 100vh;
  }

  .app-container > :first-child {
    flex: 1;
    min-height: 60vh;
  }

  .app-container > :last-child {
    flex: 0 0 40vh;
    min-width: auto;
  }
}

@media (max-width: 480px) {
  .app-container > :first-child {
    min-height: 50vh;
  }

  .app-container > :last-child {
    flex: 0 0 50vh;
  }
}
</style>

<style>
html,
body {
  height: 100%;
  overflow: hidden !important;
  position: fixed;
  width: 100vw;
}
</style>
