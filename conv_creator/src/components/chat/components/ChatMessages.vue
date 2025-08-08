<template>
  <div class="chat-messages" ref="messagesContainer">
    <ChatMessage
      v-for="message in messages"
      :key="message.id"
      :message="message"
      :current-user-id="currentUserId"
      :available-personas="availablePersonas"
      @addToChat="handleAddToChat"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import ChatMessage from './ChatMessage.vue'
import type { ChatMessage as ChatMessageType, ChatUser } from '../../../types/chat'

interface Props {
  messages: ChatMessageType[]
  currentUserId: number
  availablePersonas: ChatUser[]
}

interface Emits {
  addToChat: [text: string]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const messagesContainer = ref<HTMLElement>()

const handleAddToChat = (text: string) => {
  emit('addToChat', text)
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
