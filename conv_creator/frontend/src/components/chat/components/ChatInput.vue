<template>
  <div class="chat-input chat-input-container">
    <!-- Speaker select buttons and chips stacked vertically -->
    <div class="speaker-column">
      <div class="speaker-chip-wrapper left-speaker">
        <div class="speaker-select-wrapper" @click="toggleDropdown">
          <button class="speaker-btn">
            <span class="speaker-icon">👤</span>
            <span class="dropdown-arrow">▼</span>
          </button>
          <ul v-if="dropdownOpen" class="speaker-dropdown">
            <li v-for="user in users" :key="user.speaker" @click.stop="selectSpeaker(user.speaker)">
              {{ user.speaker }}
            </li>
          </ul>
        </div>
        <div v-if="selectedSpeaker" class="speaker-chip">
          <span class="chip-label">{{ selectedSpeaker }}</span>
          <button class="chip-remove-btn" @click.stop="removeSpeaker" aria-label="Remove speaker">
            &times;
          </button>
        </div>
      </div>

      <div class="speaker-chip-wrapper right-speaker">
        <div
          class="speaker-select-wrapper"
          ref="addresseesDropdownRef"
          @click="toggleAddresseesDropdown"
        >
          <button class="speaker-btn">
            <span class="speaker-icon">➡️</span>
            <span class="dropdown-arrow">▼</span>
          </button>
          <ul v-if="addresseesDropdownOpen" class="speaker-dropdown">
            <li
              v-for="user in users.filter((u) => u.speaker !== selectedSpeaker)"
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
            v-for="addresseee in selectedAddressees"
            :key="addresseee"
            class="speaker-chip addresseee-chip"
          >
            <span class="chip-label">{{ addresseee }}</span>
            <button
              class="chip-remove-btn"
              @click.stop="removeAddressee(addresseee)"
              aria-label="Remove addresseee"
            >
              &times;
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="input-row">
      <!-- Speaker select dropdown button -->

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
        :disabled="!selectedSpeaker || selectedAddressees.length === 0"
        :aria-disabled="!selectedSpeaker || selectedAddressees.length === 0"
      >
        ➤
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useUsers } from '../../../composables/useUsers'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  isFirstMessage: {
    type: Boolean,
    default: false,
  },
  // allow parent to control selected speaker programmatically
  selectedSpeaker: {
    type: String,
    default: '',
  },
  selectedAddressees: {
    type: Array,
    default: () => [],
  },
})
const emit = defineEmits(['update:modelValue', 'send', 'update:speaker', 'update:addressees'])
const textarea = ref(null)
const addresseesDropdownRef = ref(null)

// Speaker dropdown logic (left side)
const users = ref([])
const selectedSpeaker = ref('')
const dropdownOpen = ref(false)

// Addressees dropdown logic (right side)
const selectedAddressees = ref([])
const addresseesDropdownOpen = ref(false)

onMounted(() => {
  // load users from backend via composable. The backend now requires an explicit
  // discussion file path, so derive it from the current route (params or query).
  const route = useRoute()
  const fileParam = route?.params?.file || route?.query?.file || undefined

  const { loadUsers, availablePersonas } = useUsers()
  if (fileParam) {
    loadUsers(fileParam).then(() => {
      users.value = availablePersonas.value.map((p) => ({ speaker: p.name, ...p }))

      // If this is the first message, automatically select all users as addressees
      if (props.isFirstMessage) {
        selectedAddressees.value = users.value.map((user) => user.speaker)
        emit('update:addressees', selectedAddressees.value)
      }
    })
  } else {
    console.warn('[ChatInput] No discussion file in route; skipping loadUsers')
  }

  // Add click-outside listener
  document.addEventListener('click', handleClickOutside)

  // Initialize internal speaker from external prop if provided
  if (props.selectedSpeaker) {
    selectedSpeaker.value = props.selectedSpeaker
    // ensure parent is informed (in case it expects an update flow)
    emit('update:speaker', selectedSpeaker.value)
  }
  // Initialize internal addressees from external prop if provided
  if (
    props.selectedAddressees &&
    Array.isArray(props.selectedAddressees) &&
    props.selectedAddressees.length > 0
  ) {
    selectedAddressees.value = [...props.selectedAddressees]
    // Inform parent to keep flows consistent (no-op if identical)
    emit('update:addressees', selectedAddressees.value)
  }
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
  // Close addressees dropdown when opening speaker dropdown
  if (dropdownOpen.value) {
    addresseesDropdownOpen.value = false
  }
}

const selectSpeaker = (speaker) => {
  selectedSpeaker.value = speaker
  dropdownOpen.value = false

  // Remove the speaker from addressees if they're already selected as an addresseee
  const addresseeeIndex = selectedAddressees.value.indexOf(speaker)
  if (addresseeeIndex > -1) {
    selectedAddressees.value.splice(addresseeeIndex, 1)
    emit('update:addressees', selectedAddressees.value)
  }

  emit('update:speaker', speaker)
}

// Watch for external selectedSpeaker changes and update internal state
watch(
  () => props.selectedSpeaker,
  (newVal) => {
    if ((newVal || '') !== (selectedSpeaker.value || '')) {
      selectedSpeaker.value = newVal || ''
    }
  },
)

// Watch for external selectedAddressees changes and update internal state
watch(
  () => props.selectedAddressees,
  (newVal) => {
    const vals = Array.isArray(newVal) ? newVal : []
    // shallow compare via JSON; avoids updating reference when identical
    if (JSON.stringify(vals) !== JSON.stringify(selectedAddressees.value)) {
      selectedAddressees.value = [...vals]
    }
  },
  { deep: true },
)

const removeSpeaker = () => {
  selectedSpeaker.value = ''
  emit('update:speaker', '')
}

// Addressees functions
const toggleAddresseesDropdown = () => {
  addresseesDropdownOpen.value = !addresseesDropdownOpen.value
  // Close speaker dropdown when opening addressees dropdown
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

    // Clear speaker and addressees after sending
    selectedSpeaker.value = ''
    selectedAddressees.value = []
    emit('update:speaker', '')
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

.speaker-column {
  display: flex;
  flex-direction: column;
  width: 100%;
  margin-bottom: 8px;
  gap: 8px;
}

.speaker-chip-wrapper {
  width: 100%;
  display: flex;
  align-self: start;
  justify-content: flex-start;
  margin-top: 0;
  margin-bottom: 0;
}

.speaker-chip-wrapper.right-speaker {
  justify-content: flex-start;
}

.speaker-chip {
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

.addresseee-chip {
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
  background: #f5f7fa; /* light neutral input */
  color: #111; /* dark text for visibility on light bg */
  max-height: 90px; /* limit growth */
  overflow-y: auto;
  min-width: 0;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

textarea::placeholder {
  color: rgba(0, 0, 0, 0.35);
}

textarea:focus {
  outline: none;
  background-color: #ffffff;
  box-shadow: 0 0 0 3px rgba(100, 150, 250, 0.06);
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
  color: #006ba3;
}

.send-btn {
  background-color: #006ba3;
  color: #fff;
  border-radius: 8px;
  width: 44px;
  height: 36px;
  margin-left: 8px;
  transition: background-color 0.15s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.send-btn:hover {
  background-color: #005380;
}

.send-btn:disabled {
  background-color: rgba(0, 107, 163, 0.2);
  cursor: not-allowed;
}

/* Speaker select styles */
.speaker-select-wrapper {
  position: relative;
  margin-right: 8px;
  z-index: 20;
}
.speaker-btn {
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
.speaker-icon {
  font-size: 18px;
}
.dropdown-arrow {
  font-size: 12px;
}
.speaker-dropdown {
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
.speaker-dropdown li {
  padding: 4px 12px;
  cursor: pointer;
  color: #006ba3;
  font-size: 15px;
  white-space: nowrap;
  display: flex;
  align-items: center;
}
.speaker-dropdown li:hover {
  background: #e6f2fa;
}

@media (max-width: 700px) {
  .chat-input-container {
    max-width: 100%;
    padding: 0 4px;
  }
}
</style>
