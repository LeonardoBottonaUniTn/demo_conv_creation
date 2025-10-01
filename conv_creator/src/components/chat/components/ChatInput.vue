<template>
  <div class="chat-input chat-input-container">
    <!-- Sender select button and chip above input, left-aligned -->
    <div class="sender-chip-wrapper">
      <div class="sender-select-wrapper" @click="toggleDropdown">
        <button class="sender-btn">
          <span class="sender-icon">👤</span>
          <span class="dropdown-arrow">▼</span>
        </button>
        <ul v-if="dropdownOpen" class="sender-dropdown">
          <li v-for="user in users" :key="user.speaker" @click.stop="selectSender(user.speaker)">
            {{ user.speaker }}
          </li>
        </ul>
      </div>
      <div v-if="selectedSender" class="sender-chip">
        <span class="chip-label">{{ selectedSender }}</span>
        <button class="chip-remove-btn" @click.stop="removeSender" aria-label="Remove sender">
          &times;
        </button>
      </div>
      <!-- ...existing code... -->
    </div>
    <div class="input-row">
      <!-- Sender select dropdown button -->

      <!-- Expanding textarea -->
      <textarea
        :value="modelValue"
        ref="textarea"
        placeholder="Message"
        @input="onInput"
        @keydown.enter.exact.prevent="send"
        rows="1"
      ></textarea>
      <!-- Right-side button (send if text, mic if empty) -->
      <button v-if="modelValue.trim().length > 0" class="send-btn" @click="send">➤</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import usersData from '@/backend/bp_130_users.json'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
})
const emit = defineEmits(['update:modelValue', 'send', 'update:sender'])
const textarea = ref(null)

// Sender dropdown logic
const users = ref([])
const selectedSender = ref('OG')
const dropdownOpen = ref(false)

onMounted(() => {
  users.value = usersData
})

const toggleDropdown = () => {
  dropdownOpen.value = !dropdownOpen.value
}
const selectSender = (speaker) => {
  selectedSender.value = speaker
  dropdownOpen.value = false
  emit('update:sender', speaker)
}

const onInput = (e) => {
  emit('update:modelValue', e.target.value)
  if (e.target.value.length === 0) {
    resetHeight()
  } else {
    autoResize()
  }
}

const autoResize = () => {
  const el = textarea.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}

const resetHeight = () => {
  const el = textarea.value
  if (!el) return
  el.style.height = 'auto'
}

const send = () => {
  if (props.modelValue.trim().length > 0) {
    emit('send')
    emit('update:modelValue', '')
    resetHeight()
  }
}
</script>

<style scoped>
.chat-input-container {
  width: 100%;
  max-width: 500px;
  margin: 0 auto;
  background: #006ba3;
  box-sizing: border-box;
  border-radius: 32px;
  padding: 0 0 8px 0;
  display: flex;
  flex-direction: column;
}

.sender-chip-wrapper {
  width: 100%;
  display: flex;
  justify-content: flex-start;
  margin-top: 8px;
  margin-bottom: 2px;
}

.sender-chip {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  color: #006ba3;
  font-weight: 600;
  font-size: 15px;
  border-radius: 16px;
  padding: 0 12px;
  min-height: 32px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.07);
  width: fit-content;
  margin: 0;
  gap: 8px;
}
.chip-label {
  text-align: center;
}
.chip-remove-btn {
  background: none;
  border: none;
  color: #006ba3;
  font-size: 16px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.input-row {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0 0 0 0;
}

textarea {
  flex: 1 1 auto;
  border: none;
  outline: none;
  resize: none;
  font-size: 16px;
  line-height: 20px;
  padding: 8px;
  border-radius: 16px;
  background: #006ba3;
  max-height: 90px; /* limit growth */
  overflow-y: auto;
  min-width: 0;
}

button {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  height: 40px;
}

/* Sender select styles */
.sender-select-wrapper {
  position: relative;
  margin-right: 8px;
  z-index: 20;
}
.sender-btn {
  background: #fff;
  color: #006ba3;
  border-radius: 16px;
  border: 1px solid #006ba3;
  padding: 0 10px;
  min-width: 40px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 16px;
  height: 32px;
  cursor: pointer;
}
.sender-icon {
  font-size: 18px;
}
.dropdown-arrow {
  font-size: 12px;
}
.sender-dropdown {
  position: absolute;
  bottom: 110%; /* open upwards */
  left: 0;
  background: #fff;
  border: 1px solid #006ba3;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  z-index: 10;
  min-width: 100%;
  padding: 4px 0;
  list-style: none;
  max-height: 160px;
  overflow-y: auto;
}
.sender-dropdown li {
  padding: 4px 12px;
  cursor: pointer;
  color: #006ba3;
  font-size: 15px;
  white-space: nowrap;
}
.sender-dropdown li:hover {
  background: #e6f2fa;
}

@media (max-width: 700px) {
  .chat-input-container {
    max-width: 100%;
    padding: 0 4px;
  }
}
</style>
