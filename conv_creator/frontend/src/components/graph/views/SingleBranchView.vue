<template>
  <div class="single-branch-view">
    <div v-for="(node, index) in nodes" :key="node.id" class="argument-node-wrapper">
      <ArgumentNode
        :node="node"
        :max-text-length="100"
        :node-classes="node.type === 'thesis' ? ['root-node'] : []"
        :show-expand-hint="node.text.length > 100"
        @node-click="emit('selectNode', $event)"
      />
    </div>
    <!-- Connection lines for single branch -->
    <SingleBranchConnections
      v-if="nodes.length > 1"
      :nodes="nodes"
      :get-single-connection-start="getSingleConnectionStart"
      :get-single-connection-end="getSingleConnectionEnd"
    />
  </div>
</template>

<script setup lang="ts">
import ArgumentNode from '../nodes/ArgumentNode.vue'
import SingleBranchConnections from './SingleBranchConnections.vue'
import type { ArgumentNode as ArgumentNodeType } from '@/types/graph'

interface Props {
  nodes: ArgumentNodeType[]
  getSingleBranchPosition: (index: number) => { position: 'absolute'; left: string; top: string }
  getSingleConnectionStart: (index: number) => { x: number; y: number }
  getSingleConnectionEnd: (index: number) => { x: number; y: number }
}

interface Emits {
  selectNode: [node: ArgumentNodeType]
}

defineProps<Props>()
const emit = defineEmits<Emits>()
</script>

<style scoped>
.single-branch-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  min-height: 100%;
}

.argument-node-wrapper {
  margin-bottom: 24px;
  width: 100%;
  display: flex;
  justify-content: center;
}

/*
  To center nodes horizontally, getSingleBranchPosition(index) should return:
  {
    position: 'absolute',
    left: '50%',
    transform: 'translateX(-50%)',
    top: `${calculatedTop}px`
  }
*/

:deep(.argument-node) {
  max-width: 300px;
  font-size: 14px;
}

:deep(.root-node) {
  border-width: 4px;
  font-weight: 600;
}
</style>
