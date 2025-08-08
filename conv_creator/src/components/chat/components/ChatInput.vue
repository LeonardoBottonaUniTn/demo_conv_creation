<template>
  <div class="chat-input">
    <div class="input-controls">
      <select v-model="selectedUserId" class="user-selector">
        <option :value="currentUserId">{{ currentUserName }} (You)</option>
        <option v-for="persona in availablePersonas" :key="persona.id" :value="persona.id">
          {{ persona.name }} ({{ persona.stance }})
        </option>
      </select>
      <input
        v-model="inputText"
        @keyup.enter="handleSend"
        type="text"
        :placeholder="placeholder"
        class="message-input"
      />
      <button @click="handleSend" class="send-button" :disabled="!canSend">Send</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { ChatUser } from '../../../types/chat'

interface Props {
  placeholder?: string
  inputValue?: string
  currentUserId?: number
  currentUserName?: string
  availablePersonas?: ChatUser[]
}

interface Emits {
  send: [text: string, senderId: number]
  updateInput: [value: string]
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'Type a message...',
  inputValue: '',
  currentUserId: 1,
  currentUserName: 'You',
  availablePersonas: () => [],
})

const emit = defineEmits<Emits>()

const inputText = ref('')
const selectedUserId = ref(props.currentUserId)

// Initialize with prop value immediately
if (props.inputValue) {
  inputText.value = props.inputValue
}

// Watch for external input value changes
watch(
  () => props.inputValue,
  (newValue) => {
    inputText.value = newValue || ''
  },
  { immediate: true },
)

// Emit input changes (but avoid circular updates)
watch(inputText, (newValue) => {
  if (newValue !== props.inputValue) {
    emit('updateInput', newValue)
  }
})

const canSend = computed(() => {
  return inputText.value.trim().length > 0
})

const handleSend = () => {
  if (canSend.value) {
    emit('send', inputText.value.trim(), selectedUserId.value)
    // Don't clear here - let the parent handle it
  }
}
</script>

<style scoped>
.chat-input {
  padding: 15px;
  background-color: #006ba3;
  border-top: 1px solid #005080;
}

.input-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.user-selector {
  padding: 8px 12px;
  border: none;
  border-radius: 15px;
  background-color: rgba(255, 255, 255, 0.9);
  color: #333;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  min-width: 120px;
}

.user-selector:focus {
  outline: none;
  background-color: white;
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

.send-button:hover:not(:disabled) {
  background-color: #45a049;
}

.send-button:disabled {
  background-color: #666;
  cursor: not-allowed;
}
</style>
