<script setup lang="ts">
import { ref } from 'vue'
import DiscussionGraph from './components/graph/DiscussionGraph.vue'
import TelegramChat from './components/chat/TelegramChat.vue'

interface ChatMessage {
  id: number
  sender: string
  text: string
  time: string
}

// Sample messages for the chat simulation
const messages = ref<ChatMessage[]>([])

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
}

/* Responsive design */
@media (max-width: 768px) {
  .app-container {
    flex-direction: column;
  }
}
</style>
