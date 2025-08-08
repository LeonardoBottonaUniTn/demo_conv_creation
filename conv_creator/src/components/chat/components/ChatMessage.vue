<template>
  <div
    class="message"
    :class="{ 'own-message': message.sender === currentUserId, 'thesis-message': isThesisMessage }"
  >
    <div class="message-header" v-if="!isOwnMessage">
      <span class="sender">{{ senderName }}</span>
      <span v-if="senderStance" class="stance-badge" :class="senderStance">{{ senderStance }}</span>
    </div>
    <div class="message-text">{{ message.text }}</div>
    <div class="message-actions" v-if="isThesisMessage">
      <button @click="addToChat" class="add-to-chat-btn">Add to Chat</button>
    </div>
    <div class="message-time">{{ formatTime(message.timestamp) }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage, ChatUser } from '../../../types/chat'

interface Props {
  message: ChatMessage
  currentUserId: number
  availablePersonas: ChatUser[]
}

interface Emits {
  addToChat: [text: string]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isOwnMessage = computed(() => props.message.sender === props.currentUserId)

const isThesisMessage = computed(() => {
  // More robust detection for thesis messages
  return (
    props.message.text.toLowerCase().includes('climate change') && props.message.text.length > 100
  ) // Thesis is typically longer
})

const senderInfo = computed(() => {
  if (props.message.sender === props.currentUserId) {
    return { name: 'You', stance: null }
  }

  const persona = props.availablePersonas.find((p) => p.id === props.message.sender)
  return {
    name: persona?.name || 'Unknown',
    stance: persona?.stance || null,
  }
})

const senderName = computed(() => senderInfo.value.name)
const senderStance = computed(() => senderInfo.value.stance)

const formatTime = (timestamp: Date) => {
  return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const addToChat = () => {
  emit('addToChat', props.message.text)
}
</script>

<style scoped>
.message {
  margin-bottom: 15px;
  animation: slideIn 0.3s ease-out;
}

.message.own-message {
  text-align: right;
}

.message.own-message .message-text {
  background-color: #0088cc;
  color: white;
  margin-left: auto;
}

.message.thesis-message {
  border-left: 4px solid #ff6b35;
  padding-left: 12px;
  background-color: #fff8f5;
  border-radius: 8px;
  margin-bottom: 20px;
}

.message.thesis-message .message-text {
  background-color: #ff6b35;
  color: white;
  font-weight: 500;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
  font-size: 12px;
}

.sender {
  font-weight: 600;
  color: #333;
}

.stance-badge {
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
}

.stance-badge.positive {
  background-color: #4caf50;
  color: white;
}

.stance-badge.negative {
  background-color: #f44336;
  color: white;
}

.message-text {
  background-color: #f1f3f4;
  color: #333;
  padding: 10px 14px;
  border-radius: 18px;
  display: inline-block;
  max-width: 85%;
  word-wrap: break-word;
  font-size: 14px;
  line-height: 1.4;
}

.message-time {
  font-size: 11px;
  color: #8b98a5;
  margin-top: 4px;
}

.message.own-message .message-time {
  text-align: right;
}

.message-actions {
  margin-top: 8px;
  display: flex;
  justify-content: center;
}

.add-to-chat-btn {
  background-color: #0088cc;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
}

.add-to-chat-btn:hover {
  background-color: #006ba3;
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
</style>
