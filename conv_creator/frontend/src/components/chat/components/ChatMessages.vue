<template>
  <div class="chat-messages" ref="messagesContainer">
    <ChatMessage
      v-for="(message, index) in messages"
      :key="message.id"
      :message="message"
      :current-user="currentUser"
      :available-personas="availablePersonas"
      :turn-number="index + 1"
      @addToChat="handleAddToChat"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import ChatMessage from './ChatMessage.vue'
import type { ChatMessage as ChatMessageType, User } from '../../../types/chat'
import type { AddToChatPayload } from '@/types/graph'

interface Props {
  messages: ChatMessageType[]
  currentUser: User
  availablePersonas: User[]
}

interface Emits {
  addToChat: [payload: AddToChatPayload]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const messagesContainer = ref<HTMLElement>()

const handleAddToChat = (payload: AddToChatPayload) => {
  // Pass through the normalized payload up to parent
  emit('addToChat', payload)
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

// Expose scroll method for external use
defineExpose({
  scrollToBottom: () => {
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  },
})
</script>

<style scoped>
.chat-messages {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
  background-color: #0088cc;
}
</style>
