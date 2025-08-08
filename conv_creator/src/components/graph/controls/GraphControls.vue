<template>
  <div class="graph-controls">
    <button @click="toggleView" :class="{ active: showAllBranches }" class="view-toggle-button">
      {{ showAllBranches ? 'Show Single Branch' : 'Show All Branches' }}
    </button>
    <div v-if="!showAllBranches" class="branch-controls">
      <button
        v-for="(branch, index) in branches"
        :key="index"
        @click="selectBranch(index)"
        :class="{ active: selectedBranch === index }"
        class="branch-button"
      >
        Branch {{ index + 1 }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { BranchesData } from '@/types/graph'

interface Props {
  showAllBranches: boolean
  branches: BranchesData
  selectedBranch: number
}

interface Emits {
  toggleView: []
  selectBranch: [index: number]
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const toggleView = () => {
  emit('toggleView')
}

const selectBranch = (index: number) => {
  emit('selectBranch', index)
}
</script>

<style scoped>
.graph-controls {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.branch-button {
  padding: 8px 16px;
  border: 2px solid #6c757d;
  background: white;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
}

.branch-button:hover {
  background-color: #6c757d;
  color: white;
}

.branch-button.active {
  background-color: #007bff;
  border-color: #007bff;
  color: white;
}

.view-toggle-button {
  padding: 10px 20px;
  border: 2px solid #28a745;
  background: white;
  border-radius: 25px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
  font-size: 14px;
}

.view-toggle-button:hover {
  background-color: #28a745;
  color: white;
}

.view-toggle-button.active {
  background-color: #28a745;
  border-color: #28a745;
  color: white;
}

.branch-controls {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
