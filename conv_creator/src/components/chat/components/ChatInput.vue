<template>
  <div class="chat-input chat-input-container">
    <!-- Sender select buttons and chips stacked vertically -->
    <div class="sender-column">
      <div class="sender-chip-wrapper left-sender">
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
      </div>

      <div class="sender-chip-wrapper right-sender">
        <div
          class="sender-select-wrapper"
          ref="addresseesDropdownRef"
          @click="toggleAddresseesDropdown"
        >
          <button class="sender-btn">
            <span class="sender-icon">➡️</span>
            <span class="dropdown-arrow">▼</span>
          </button>
          <ul v-if="addresseesDropdownOpen" class="sender-dropdown">
            <li
              v-for="user in users.filter((u) => u.speaker !== selectedSender)"
              :key="user.speaker"
              @click.stop="toggleAddressee(user.speaker)"
            >
              <span
                class="checkbox"
                :class="{ checked: selectedAddressees.includes(user.speaker) }"
              >
                {{ selectedAddressees.includes(user.speaker) ? '✓' : '' }}
              </span>
              {{ user.speaker }}
            </li>
          </ul>
        </div>
        <div v-if="selectedAddressees.length > 0" class="addressees-chips">
          <div
            v-for="addressee in selectedAddressees"
            :key="addressee"
            class="sender-chip addressee-chip"
          >
            <span class="chip-label">{{ addressee }}</span>
            <button
              class="chip-remove-btn"
              @click.stop="removeAddressee(addressee)"
              aria-label="Remove addressee"
            >
              &times;
            </button>
          </div>
        </div>
      </div>
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
      <button
        v-if="modelValue.trim().length > 0"
        class="send-btn"
        @click="send"
        :disabled="!selectedSender || selectedAddressees.length === 0"
        :aria-disabled="!selectedSender || selectedAddressees.length === 0"
      >
        ➤
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import usersData from '@/backend/bp_130_users.json'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  isFirstMessage: {
    type: Boolean,
    default: false,
  },
})
const emit = defineEmits(['update:modelValue', 'send', 'update:sender', 'update:addressees'])
const textarea = ref(null)
const addresseesDropdownRef = ref(null)

// Sender dropdown logic (left side)
const users = ref([])
const selectedSender = ref('')
const dropdownOpen = ref(false)

// Addressees dropdown logic (right side)
const selectedAddressees = ref([])
const addresseesDropdownOpen = ref(false)

onMounted(() => {
  users.value = usersData

  // If this is the first message, automatically select all users as addressees
  if (props.isFirstMessage) {
    selectedAddressees.value = users.value.map((user) => user.speaker)
    emit('update:addressees', selectedAddressees.value)
  }

  // Add click-outside listener
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  // Remove click-outside listener
  document.removeEventListener('click', handleClickOutside)
})

// Handle click outside dropdown
const handleClickOutside = (event) => {
  if (addresseesDropdownRef.value && !addresseesDropdownRef.value.contains(event.target)) {
    addresseesDropdownOpen.value = false
  }
}

// Watch for external changes to modelValue and trigger auto-resize
watch(
  () => props.modelValue,
  (newVal) => {
    nextTick(() => {
      if (newVal && newVal.trim().length > 0) {
        autoResize()
      } else {
        resetHeight()
      }
    })
  },
)

const toggleDropdown = () => {
  dropdownOpen.value = !dropdownOpen.value
  // Close addressees dropdown when opening sender dropdown
  if (dropdownOpen.value) {
    addresseesDropdownOpen.value = false
  }
}

const selectSender = (speaker) => {
  selectedSender.value = speaker
  dropdownOpen.value = false

  // Remove the sender from addressees if they're already selected as an addressee
  const addresseeIndex = selectedAddressees.value.indexOf(speaker)
  if (addresseeIndex > -1) {
    selectedAddressees.value.splice(addresseeIndex, 1)
    emit('update:addressees', selectedAddressees.value)
  }

  emit('update:sender', speaker)
}

const removeSender = () => {
  selectedSender.value = ''
  emit('update:sender', '')
}

// Addressees functions
const toggleAddresseesDropdown = () => {
  addresseesDropdownOpen.value = !addresseesDropdownOpen.value
  // Close sender dropdown when opening addressees dropdown
  if (addresseesDropdownOpen.value) {
    dropdownOpen.value = false
  }
}

const toggleAddressee = (speaker) => {
  const index = selectedAddressees.value.indexOf(speaker)
  if (index > -1) {
    // Remove if already selected
    selectedAddressees.value.splice(index, 1)
  } else {
    // Add if not selected
    selectedAddressees.value.push(speaker)
  }
  emit('update:addressees', selectedAddressees.value)
  // Don't close dropdown to allow multiple selections
}

const removeAddressee = (speaker) => {
  const index = selectedAddressees.value.indexOf(speaker)
  if (index > -1) {
    selectedAddressees.value.splice(index, 1)
    emit('update:addressees', selectedAddressees.value)
  }
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

    // Clear sender and addressees after sending
    selectedSender.value = ''
    selectedAddressees.value = []
    emit('update:sender', '')
    emit('update:addressees', [])
  }
}
</script>

<style scoped>
.chat-input-container {
  width: 100%;
  max-width: 500px;
  margin: 0 auto;
  background: transparent;
  box-sizing: border-box;
  border-radius: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.sender-column {
  display: flex;
  flex-direction: column;
  width: 100%;
  margin-bottom: 8px;
  gap: 8px;
}

.sender-chip-wrapper {
  width: 100%;
  display: flex;
  align-self: start;
  justify-content: flex-start;
  margin-top: 0;
  margin-bottom: 0;
}

.sender-chip-wrapper.right-sender {
  justify-content: flex-start;
}

.sender-chip {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  color: #006ba3;
  font-weight: 600;
  font-size: 16px;
  border-radius: 16px;
  padding: 0 10px;
  height: 32px;
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

/* Addressees styles */
.addressees-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.addressee-chip {
  background: #e8f4f8;
  color: #006ba3;
  font-size: 14px;
  height: 28px;
  min-height: 28px;
}

.checkbox {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 1px solid #006ba3;
  border-radius: 3px;
  margin-right: 8px;
  text-align: center;
  line-height: 14px;
  font-size: 12px;
  background: #fff;
}

.checkbox.checked {
  background: #006ba3;
  color: white;
}

.input-row {
  display: flex;
  align-items: flex-end;
  width: 100%;
  padding: 0;
  gap: 8px;
}

textarea {
  flex: 1 1 auto;
  border: none;
  outline: none;
  resize: none;
  font-size: 16px;
  line-height: 20px;
  padding: 12px 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  max-height: 90px; /* limit growth */
  overflow-y: auto;
  min-width: 0;
}

textarea::placeholder {
  color: rgba(255, 255, 255, 0.6);
}

textarea:focus {
  outline: none;
  background-color: rgba(255, 255, 255, 0.15);
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
  color: white;
}

.send-btn {
  background-color: #4caf50;
  color: white;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  margin-left: 8px;
  transition: background-color 0.2s;
}

.send-btn:hover {
  background-color: #45a049;
}

.send-btn:disabled {
  background-color: rgba(255, 255, 255, 0.3);
  cursor: not-allowed;
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
  display: flex;
  align-items: center;
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
