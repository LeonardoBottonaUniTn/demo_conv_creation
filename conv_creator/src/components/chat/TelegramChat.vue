<template>
  <div class="chat-section">
    <div class="chat-header">
      <h3>{{ title }}</h3>
      <div class="chat-status">
        <span class="status-indicator"></span>
        {{ status }}
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="message in messages"
        :key="message.id"
        class="message"
        :class="{ 'own-message': message.sender === currentUser }"
      >
        <div class="message-header">
          <span class="sender">{{ message.sender }}</span>
          <span class="time">{{ message.time }}</span>
        </div>
        <div class="message-text">{{ message.text }}</div>
      </div>
    </div>

    <div class="chat-input">
      <input
        v-model="newMessage"
        @keyup.enter="sendMessage"
        type="text"
        :placeholder="inputPlaceholder"
        class="message-input"
      />
      <button @click="sendMessage" class="send-button">Send</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'

interface ChatMessage {
  id: number
  sender: string
  text: string
  time: string
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
  status: 'Online',
  currentUser: 'You',
  inputPlaceholder: 'Type a message...',
  inputValue: '',
})

const emit = defineEmits<{
  sendMessage: [message: { sender: string; text: string; time: string }]
  updateInput: [value: string]
}>()

const newMessage = ref('')
const messagesContainer = ref<HTMLElement>()

// Watch for changes in inputValue prop and update newMessage
watch(
  () => props.inputValue,
  (newValue) => {
    if (newValue !== undefined && newValue !== newMessage.value) {
      newMessage.value = newValue
    }
  },
  { immediate: true },
)

// Emit input changes back to parent
watch(newMessage, (newValue) => {
  emit('updateInput', newValue)
})

const sendMessage = () => {
  if (newMessage.value.trim()) {
    const message = {
      sender: props.currentUser,
      text: newMessage.value,
      time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    }
    emit('sendMessage', message)
    newMessage.value = ''

    // Auto-scroll to bottom
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  }
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
</script>

<style scoped>
/* Right side - Chat section (1/4 width) */
.chat-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #0088cc;
  color: white;
}

.chat-header {
  padding: 15px 20px;
  background-color: #006ba3;
  border-bottom: 1px solid #005080;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.chat-status {
  display: flex;
  align-items: center;
  font-size: 12px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  background-color: #4caf50;
  border-radius: 50%;
  margin-right: 5px;
}

.chat-messages {
  flex: 1;
  padding: 15px;
  overflow-y: auto;
  background-color: #0088cc;
}

.message {
  margin-bottom: 15px;
  animation: slideIn 0.3s ease-out;
}

.message.own-message {
  text-align: right;
}

.message.own-message .message-text {
  background-color: #4caf50;
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

.time {
  font-size: 10px;
}

.message-text {
  background-color: rgba(255, 255, 255, 0.1);
  padding: 8px 12px;
  border-radius: 18px;
  display: inline-block;
  max-width: 80%;
  word-wrap: break-word;
  font-size: 14px;
  line-height: 1.4;
}

.chat-input {
  padding: 15px;
  background-color: #006ba3;
  border-top: 1px solid #005080;
  display: flex;
  gap: 10px;
}

.message-input {
  flex: 1;
  padding: 10px 15px;
  border: none;
  border-radius: 20px;
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 14px;
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
