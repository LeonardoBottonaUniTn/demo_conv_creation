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
      <!-- ChatInput component for message input and send -->
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
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue'
import ChatInput from './components/ChatInput.vue'

interface ChatMessage {
  id: number
  sender: string
  text: string
  time: string
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
  status: 'Online',
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
  padding: 15px 5px;
  background-color: #006ba3;
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.sender-chip {
  display: flex;
  align-items: center;
  background: #fff;
  color: #0088cc;
  border-radius: 16px;
  padding: 4px 12px;
  margin-right: 8px;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
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
