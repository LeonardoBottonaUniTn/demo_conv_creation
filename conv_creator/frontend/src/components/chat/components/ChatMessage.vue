<template>
  <div
    class="message"
    :class="{
      'own-message': message.speaker === currentUser.name,
    }"
  >
    <div class="message-header" v-if="!isOwnMessage">
      <div class="message-meta">
        <span class="speaker">{{ speakerName }}</span>
        <span v-if="message.addressees && message.addressees.length > 0" class="addressees"
          >→{{ message.addressees.join(',') }}</span
        >
      </div>
    </div>
    <div class="message-text">{{ message.text }}</div>
    <div class="message-actions">
      <button @click="addToChat" class="add-to-chat-btn">Add to Chat</button>
    </div>
    <div class="message-turn">Turn {{ turnNumber }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage, User } from '../../../types/chat'

interface Props {
  message: ChatMessage
  currentUser: User
  availablePersonas: User[]
  turnNumber: number
}

import type { AddToChatPayload } from '@/types/graph'

interface Emits {
  addToChat: [payload: AddToChatPayload]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isOwnMessage = computed(() => props.message.speaker === props.currentUser.name)

const speakerInfo = computed(() => {
  const persona = props.availablePersonas.find((p) => p.name === props.message.speaker)
  return {
    name: persona?.name || 'Unknown',
    description: persona?.description || null,
  }
})

const speakerName = computed(() => speakerInfo.value.name)
const speakerDescription = computed(() => speakerInfo.value.description)

const addToChat = () => {
  // Emit a normalized payload so receivers can rely on a single contract
  const payload: AddToChatPayload = {
    text: props.message.text,
    source: 'chat',
  }
  emit('addToChat', payload)
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

.message-header {
  /* Keep header as a normal block; inner .message-meta will control layout */
  margin-bottom: 5px;
  font-size: 12px;
}

.message-meta {
  display: inline-flex;
  gap: 0;
  align-items: center;
}

.speaker {
  margin-right: 0;
  font-weight: 600;
  color: #333;
}

.addressees {
  color: #666;
  font-style: italic;
  font-size: 11px;
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

.message-turn {
  font-size: 11px;
  color: #8b98a5;
  margin-top: 4px;
}

.message.own-message .message-turn {
  text-align: right;
}
/* 
.message-actions {
  margin-top: 8px;
  display: flex;
  justify-content: center;
} */

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
