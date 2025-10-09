<template>
  <div class="graph-section">
    <div class="graph-header">
      <h2>{{ title }}</h2>
      <GraphControls
        :show-all-branches="showAllBranches"
        :branches="discussionBranches"
        :selected-branch="selectedBranch"
        @toggle-view="handleToggleView"
        @select-branch="handleSelectBranch"
      />
    </div>

    <div class="graph-container" ref="graphContainer">
      <div v-if="loading" class="loading">Loading discussion data...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else class="graph-visualization">
        <!-- D3Tree visualization for testing -->
        <D3Tree
          :treeData="currentBranchNodes"
          :width="800"
          :height="600"
          @addToChat="handleAddToChat"
        />
      </div>
    </div>

    <!-- Node detail modal -->
    <Modal
      :is-visible="!!selectedNode"
      :title="selectedNode ? `${selectedNode.type.toUpperCase()} - ${selectedNode.id}` : ''"
      :content="selectedNode?.text || ''"
      @close="handleCloseModal"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import GraphControls from './controls/GraphControls.vue'
import Modal from '../shared/Modal.vue'
import { useGraphData } from '../../composables/useGraphData'
import { useGraphPositions } from '../../composables/useGraphPositions'
import type { ArgumentNode, ChatMessage } from '../../types/graph'
import D3Tree from './D3Tree.vue'

interface Props {
  title?: string
}

interface Emits {
  addMessage: [message: ChatMessage]
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Climate Change Discussion',
})

const emit = defineEmits<Emits>()

// Graph container ref
const graphContainer = ref<HTMLElement>()

// Use composables
const {
  discussionBranches,
  selectedBranch,
  loading,
  error,
  currentBranchNodes,
  thesisNode,
  loadDiscussionData,
  expandBranch,
  isBranchExpanded,
  expandedBranches,
} = useGraphData()

const {
  getBranchColor,
  getThesisConnectionStart,
  getBranchConnectionEnd,
  getSingleBranchPosition,
  getSingleConnectionStart,
  getSingleConnectionEnd,
} = useGraphPositions(graphContainer)

// Local state
const selectedNode = ref<ArgumentNode | null>(null)
const showAllBranches = ref(true)

// Event handlers
const handleToggleView = () => {
  showAllBranches.value = !showAllBranches.value
}

const handleSelectBranch = (index: number) => {
  selectedBranch.value = index
}

const handleSelectNode = (node: ArgumentNode) => {
  selectedNode.value = node
}

const handleCloseModal = () => {
  selectedNode.value = null
}

const handleAddToChat = (node: ArgumentNode, branchIndex: number) => {
  // Create a message from the selected node
  const message: ChatMessage = {
    text: node.text,
    type: 'user',
    nodeId: node.id,
    nodeType: node.type,
  }

  // Emit the message to the parent component
  emit('addMessage', message)

  // Expand this branch to show the next layer
  expandBranch(branchIndex)

  // Optional: Show a brief confirmation
  console.log(`Added to chat: ${node.type} - ${node.text.substring(0, 50)}...`)
  console.log(`Expanded branch ${branchIndex + 1}`)
}

// Initialize data
onMounted(() => {
  loadDiscussionData()
})
</script>

<style scoped>
.graph-section {
  flex: 1;
  padding: 20px;
  background-color: #f8f9fa;
  border-right: 2px solid #e9ecef;
  overflow: hidden;
  position: relative;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.graph-header {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
  flex-shrink: 0;
}

.graph-header h2 {
  margin: 0;
  color: #343a40;
  font-size: 24px;
}

.graph-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: relative;
  overflow: auto;
  flex: 1;
  min-height: 0;
}

.loading,
.error {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  font-size: 18px;
  color: #6c757d;
}

.error {
  color: #dc3545;
}

.graph-visualization {
  position: relative;
  min-height: 100%;
  width: 100%;
}

/* Responsive design */
@media (max-width: 1200px) {
  .graph-container {
    padding: 15px;
  }

  .graph-header h2 {
    font-size: 20px;
  }
}

@media (max-width: 768px) {
  .graph-section {
    padding: 15px;
  }

  .graph-header {
    flex-direction: column;
    align-items: stretch;
    margin-bottom: 15px;
  }

  .graph-container {
    padding: 10px;
  }

  .graph-header h2 {
    font-size: 18px;
  }
}

@media (max-width: 480px) {
  .graph-section {
    padding: 10px;
  }

  .graph-container {
    padding: 8px;
  }
}
</style>
