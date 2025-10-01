<template>
  <div class="chat-input chat-input-container">
    <!-- Attach button (always visible on the left) -->
    <button class="attach-btn">📎</button>

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
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
})
const emit = defineEmits(['update:modelValue', 'send'])
const textarea = ref(null)

const onInput = (e) => {
  emit('update:modelValue', e.target.value)
  autoResize()
}

const autoResize = () => {
  const el = textarea.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}

const send = () => {
  if (props.modelValue.trim().length > 0) {
    emit('send')
    emit('update:modelValue', '')
    autoResize()
  }
}
</script>

<style scoped>
.chat-input-container {
  width: 100%;
  max-width: 500px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  background: #006ba3;
  box-sizing: border-box;
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

.attach-btn {
  color: #888;
  min-width: 40px;
}

@media (max-width: 700px) {
  .chat-input-container {
    max-width: 100%;
    padding: 0 4px;
  }
}
</style>
