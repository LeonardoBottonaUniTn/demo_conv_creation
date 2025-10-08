<template>
  <svg class="connection-lines">
    <line
      v-for="(node, index) in connectableNodes"
      :key="`line-${node.id}`"
      :x1="getSingleConnectionStart(index + 1).x"
      :y1="getSingleConnectionStart(index + 1).y"
      :x2="getSingleConnectionEnd(index + 1).x"
      :y2="getSingleConnectionEnd(index + 1).y"
      :class="`connection-line connection-${node.type}`"
      stroke-linecap="round"
    />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ArgumentNode } from '@/types/graph'

interface Props {
  nodes: ArgumentNode[]
  getSingleConnectionStart: (index: number) => { x: number; y: number }
  getSingleConnectionEnd: (index: number) => { x: number; y: number }
}

const props = defineProps<Props>()

// Each line connects node i-1 to node i (skip first node)
const connectableNodes = computed(() => {
  return props.nodes.slice(1)
})
</script>

<style scoped>
.connection-lines {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.connection-line {
  stroke-width: 3;
  stroke: #6c757d;
  opacity: 0.6;
}

.connection-pro {
  stroke: #007bff;
}

.connection-con {
  stroke: #dc3545;
}
</style>
