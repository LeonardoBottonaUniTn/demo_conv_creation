<template>
  <div
    :class="['argument-node', `node-${node.type}`, ...nodeClasses]"
    @click="handleNodeClick"
    :title="nodeTitle"
  >
    <div class="node-header">
      <span class="node-id">{{ node.id }}</span>
      <span class="node-type">{{ node.type.toUpperCase() }}</span>
    </div>
    <div class="node-content">
      {{ truncatedText }}
    </div>
    <div v-if="showAddToChat" class="add-to-chat-hint" @click.stop="handleAddToChat">
      <span>{{ addToChatText }}</span>
    </div>
    <div v-if="showExpandHint" class="node-expand">Click to expand...</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ArgumentNode } from '@/types/graph'

interface Props {
  node: ArgumentNode
  maxTextLength?: number
  showAddToChat?: boolean
  addToChatText?: string
  nodeClasses?: string[]
  nodeTitle?: string
  showExpandHint?: boolean
}

interface Emits {
  nodeClick: [node: ArgumentNode]
  addToChat: [node: ArgumentNode]
}

const props = withDefaults(defineProps<Props>(), {
  maxTextLength: 100,
  showAddToChat: false,
  addToChatText: 'Add to chat',
  nodeClasses: () => [],
  nodeTitle: '',
  showExpandHint: false,
})

const emit = defineEmits<Emits>()

const truncatedText = computed(() => {
  const { text } = props.node
  const { maxTextLength } = props
  return text.length > maxTextLength ? text.substring(0, maxTextLength) + '...' : text
})

const handleNodeClick = () => {
  emit('nodeClick', props.node)
}

const handleAddToChat = () => {
  emit('addToChat', props.node)
}
</script>

<style scoped>
.argument-node {
  background: white;
  border: 3px solid #dee2e6;
  border-radius: 15px;
  padding: 20px;
  max-width: 350px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.3s ease;
  z-index: 10;
}

.argument-node:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

.node-thesis {
  border-color: #28a745;
  background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
}

.node-pro {
  border-color: #007bff;
  background: linear-gradient(135deg, #cce7ff 0%, #b8d9ff 100%);
}

.node-con {
  border-color: #dc3545;
  background: linear-gradient(135deg, #f8d7da 0%, #f1b0b7 100%);
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
  color: #6c757d;
}

.node-type {
  padding: 4px 8px;
  border-radius: 8px;
  background-color: rgba(0, 0, 0, 0.1);
}

.node-content {
  font-size: 14px;
  line-height: 1.4;
  color: #333;
}

.node-expand {
  margin-top: 8px;
  font-size: 12px;
  color: #007bff;
  font-style: italic;
}

.add-to-chat-hint {
  margin-top: 8px;
  padding: 6px 12px;
  background: rgba(0, 123, 255, 0.15);
  border-radius: 15px;
  text-align: center;
  font-size: 10px;
  color: #007bff;
  font-weight: 600;
  border: 1px solid rgba(0, 123, 255, 0.3);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.add-to-chat-hint:hover {
  background: rgba(0, 123, 255, 0.25);
  color: #0056b3;
  border-color: rgba(0, 123, 255, 0.5);
  transform: translateY(-1px);
}
</style>
