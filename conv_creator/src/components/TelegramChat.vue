<template>
  <div class="telegram-chat">
    <ChatHeader
      :current-user="currentUser"
      :other-user="currentPersona"
      :is-typing="isTyping"
      @clear-chat="clearChat"
    />

    <div class="persona-selector">
      <label>Chat with:</label>
      <select @change="handlePersonaChange" :value="currentPersona.id">
        <option v-for="persona in availablePersonas" :key="persona.id" :value="persona.id">
          {{ persona.name }} ({{ persona.stance }})
        </option>
      </select>
    </div>

    <ChatMessages
      ref="chatMessagesRef"
      :messages="messages"
      :current-user-id="currentUser.id"
      :available-personas="availablePersonas"
      @addToChat="handleAddToChat"
    />

    <ChatInput
      @send="sendMessage"
      placeholder="Type a message..."
      :inputValue="currentInputValue"
      @updateInput="handleInputUpdate"
      :currentUserId="currentUser.id"
      :currentUserName="currentUser.name"
      :availablePersonas="availablePersonas"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, computed } from 'vue'
import ChatHeader from './chat/components/ChatHeader.vue'
import ChatMessages from './chat/components/ChatMessages.vue'
import ChatInput from './chat/components/ChatInput.vue'
import type { ChatMessage } from '../types/chat'
import { useUsers } from '../composables/useUsers'

const {
  currentUser,
  availablePersonas,
  currentPersona,
  switchPersona,
  getPersonaResponses,
  getRandomPersona,
  getThesisStatement,
} = useUsers()

// Initialize input with thesis statement
const initialInputValue = ref(getThesisStatement())

// Computed property to ensure we always have the thesis statement
const currentInputValue = computed({
  get: () => {
    // Always return thesis statement if the input is empty
    const current = initialInputValue.value
    return current && current.trim() !== '' ? current : getThesisStatement()
  },
  set: (value: string) => {
    initialInputValue.value = value
  },
})

// Get random persona for thesis statement
const thesisAuthor = getRandomPersona()

const messages = ref<ChatMessage[]>([
  {
    id: 1,
    text: getThesisStatement(),
    sender: thesisAuthor.id,
    timestamp: new Date(Date.now() - 120000), // 2 minutes ago
  },
])

const isTyping = ref(false)
const chatMessagesRef = ref<InstanceType<typeof ChatMessages>>()

const handlePersonaChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  const personaId = parseInt(target.value)
  switchPersona(personaId)

  // Add a system message about the persona switch
  const switchMessage: ChatMessage = {
    id: Date.now(),
    text: `You are now chatting with ${currentPersona.value.name}. ${currentPersona.value.description}`,
    sender: currentPersona.value.id,
    timestamp: new Date(),
  }
  messages.value.push(switchMessage)

  nextTick(() => {
    chatMessagesRef.value?.scrollToBottom()
  })
}

const handleInputUpdate = (value: string) => {
  currentInputValue.value = value
}

const handleAddToChat = (text: string) => {
  currentInputValue.value = text
}

const sendMessage = (text: string, senderId: number) => {
  const message: ChatMessage = {
    id: Date.now(),
    text,
    sender: senderId,
    timestamp: new Date(),
  }

  messages.value.push(message)

  // Clear the input after sending
  currentInputValue.value = ''

  nextTick(() => {
    chatMessagesRef.value?.scrollToBottom()
  })

  // Only simulate typing and response if the message is not from the current user
  // and not from one of the personas (to avoid auto-responses from personas)
  if (senderId === currentUser.id) {
    // Simulate typing and response
    setTimeout(() => {
      isTyping.value = true
      setTimeout(() => {
        isTyping.value = false
        simulateResponse()
      }, 1500)
    }, 500)
  }
}

const simulateResponse = () => {
  const responses = getPersonaResponses(currentPersona.value.stance || 'positive')

  const response: ChatMessage = {
    id: Date.now(),
    text: responses[Math.floor(Math.random() * responses.length)],
    sender: currentPersona.value.id,
    timestamp: new Date(),
  }

  messages.value.push(response)
  nextTick(() => {
    chatMessagesRef.value?.scrollToBottom()
  })
}

const clearChat = () => {
  // Always keep the thesis statement as the first message
  const newThesisAuthor = getRandomPersona()
  messages.value = [
    {
      id: Date.now(),
      text: getThesisStatement(),
      sender: newThesisAuthor.id,
      timestamp: new Date(),
    },
  ]

  // Reset input to thesis statement
  currentInputValue.value = getThesisStatement()

  nextTick(() => {
    chatMessagesRef.value?.scrollToBottom()
  })
}

onMounted(() => {
  // Force set the input value to thesis statement on app start
  nextTick(() => {
    currentInputValue.value = getThesisStatement()
    chatMessagesRef.value?.scrollToBottom()
  })
})
</script>

<style scoped>
.telegram-chat {
  display: flex;
  flex-direction: column;
  height: 600px;
  max-width: 400px;
  background-color: #ffffff;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.persona-selector {
  padding: 10px 15px;
  background-color: #f0f2f5;
  border-bottom: 1px solid #e1e8ed;
  display: flex;
  align-items: center;
  gap: 10px;
}

.persona-selector label {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  white-space: nowrap;
}

.persona-selector select {
  flex: 1;
  padding: 5px 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
  background-color: white;
  font-size: 12px;
  cursor: pointer;
}

.persona-selector select:focus {
  outline: none;
  border-color: #0088cc;
}
</style>
