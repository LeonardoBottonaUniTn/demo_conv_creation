<template>
  <svg class="tree-connections">
    <!-- Lines from thesis to first level -->
    <line
      v-for="(branch, branchIndex) in validBranches"
      :key="`thesis-line-${branchIndex}`"
      :x1="getThesisConnectionStart().x"
      :y1="getThesisConnectionStart().y"
      :x2="getBranchConnectionEnd(branchIndex, validBranches.length).x"
      :y2="getBranchConnectionEnd(branchIndex, validBranches.length).y"
      class="tree-connection"
      :style="{ stroke: getBranchColor(branchIndex) }"
    />

    <!-- Lines from first level to expanded nodes -->
    <template v-for="(branch, branchIndex) in branches" :key="`expanded-${branchIndex}`">
      <line
        v-if="expandedBranches.has(branchIndex) && branch.length > 2"
        v-for="nodeIndex in Math.min(2, branch.length - 2)"
        :key="`expanded-line-${branchIndex}-${nodeIndex}`"
        :x1="getBranchConnectionEnd(branchIndex, validBranches.length).x"
        :y1="getBranchConnectionEnd(branchIndex, validBranches.length).y + 100"
        :x2="getBranchConnectionEnd(branchIndex, validBranches.length).x"
        :y2="
          getBranchConnectionEnd(branchIndex, validBranches.length).y + 160 + (nodeIndex - 1) * 120
        "
        class="tree-connection expanded-connection"
        :style="{ stroke: getBranchColor(branchIndex), strokeDasharray: '5,5' }"
      />
    </template>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BranchesData } from '@/types/graph'

interface Props {
  branches: BranchesData
  expandedBranches: Set<number>
  getThesisConnectionStart: () => { x: number; y: number }
  getBranchConnectionEnd: (index: number, totalBranches: number) => { x: number; y: number }
  getBranchColor: (index: number) => string
}

const props = defineProps<Props>()

const validBranches = computed(() => {
  return props.branches.filter((branch) => branch.length > 1)
})
</script>

<style scoped>
.tree-connections {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
  overflow: visible;
  min-height: 100%;
}

.tree-connection {
  stroke-width: 2;
  opacity: 0.7;
  stroke-linecap: round;
}

.expanded-connection {
  stroke-width: 1.5;
  opacity: 0.5;
  animation: dashMove 2s linear infinite;
}

@keyframes dashMove {
  0% {
    stroke-dashoffset: 0;
  }
  100% {
    stroke-dashoffset: 10;
  }
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .tree-connection {
    stroke-width: 1.5;
  }

  .expanded-connection {
    stroke-width: 1;
  }
}
</style>
