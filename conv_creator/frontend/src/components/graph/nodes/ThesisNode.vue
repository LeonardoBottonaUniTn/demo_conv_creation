<template>
  <div class="thesis-node" @click="handleClick" :style="nodeStyle">
    <div class="node-header">
      <span class="node-id">{{ node.id }}</span>
      <span class="node-type">{{ node.id.toUpperCase() }}</span>
    </div>
    <div class="node-content">
      {{ truncatedText }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ArgumentNode } from '@/types/graph'
import { getSpeakerColors } from '@/composables/useSpeakerColors'

interface Props {
  node: ArgumentNode
  maxTextLength?: number
}

interface Emits {
  click: [node: ArgumentNode]
}

const props = withDefaults(defineProps<Props>(), {
  maxTextLength: 80,
})

const emit = defineEmits<Emits>()

const truncatedText = computed(() => {
  const { text } = props.node
  const { maxTextLength } = props
  return text.length > maxTextLength ? text.substring(0, maxTextLength) + '...' : text
})

const handleClick = () => {
  emit('click', props.node)
}

const nodeStyle = computed(() => {
  const c = getSpeakerColors(props.node?.speaker || '')
  return {
    background: c.background || 'linear-gradient(135deg, #2196f3, #1976d2)',
    color: c.onBackground || 'white',
  }
})
</script>

<style scoped>
.thesis-node {
  background: linear-gradient(135deg, #2196f3, #1976d2);
  color: white;
  font-weight: bold;
  font-size: 14px;
  max-width: 300px;
  padding: 20px;
  border-radius: 15px;
  box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);
  cursor: pointer;
  transition: all 0.3s ease;
}

.thesis-node:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 20px rgba(33, 150, 243, 0.4);
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 600;
}

.node-id {
  color: rgba(255, 255, 255, 0.8);
}

.node-type {
  padding: 4px 8px;
  border-radius: 8px;
  background-color: rgba(255, 255, 255, 0.2);
}

.node-content {
  font-size: 14px;
  line-height: 1.4;
  color: white;
}
</style>
