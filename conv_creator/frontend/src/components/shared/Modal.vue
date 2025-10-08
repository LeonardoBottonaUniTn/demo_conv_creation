<template>
  <div v-if="isVisible" class="node-modal" @click="handleBackdropClick">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>{{ title }}</h3>
        <button @click="handleClose" class="close-button">&times;</button>
      </div>
      <div class="modal-body">
        <slot>
          <p>{{ content }}</p>
        </slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  isVisible: boolean
  title?: string
  content?: string
  closeOnBackdrop?: boolean
}

interface Emits {
  close: []
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Details',
  content: '',
  closeOnBackdrop: true,
})

const emit = defineEmits<Emits>()

const handleClose = () => {
  emit('close')
}

const handleBackdropClick = () => {
  if (props.closeOnBackdrop) {
    handleClose()
  }
}
</script>

<style scoped>
.node-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 15px;
  padding: 30px;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 2px solid #dee2e6;
  padding-bottom: 15px;
}

.modal-header h3 {
  margin: 0;
  color: #333;
}

.close-button {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #6c757d;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-button:hover {
  color: #333;
}

.modal-body p {
  font-size: 16px;
  line-height: 1.6;
  margin: 0;
  color: #333;
}
</style>
