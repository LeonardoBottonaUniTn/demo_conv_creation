<template>
  <div class="tree-view">
    <!-- Thesis node (root) centered at top -->
    <div class="tree-thesis">
      <ThesisNode :node="thesisNode" @click="emit('selectNode', $event)" />
    </div>

    <!-- First layer nodes only (immediate children) -->
    <div class="tree-branches">
      <div v-for="(branch, branchIndex) in branches" :key="branchIndex" class="branch-column">
        <div class="branch-header" :style="{ backgroundColor: getBranchColor(branchIndex) }">
          Branch {{ branchIndex + 1 }}
          <span v-if="isBranchExpanded(branchIndex)" class="expanded-indicator">📖</span>
        </div>

        <!-- First level node -->
        <ArgumentNode
          v-if="branch.length > 1"
          :node="branch[1]"
          :max-text-length="60"
          :show-add-to-chat="true"
          add-to-chat-text="Add to chat"
          :node-classes="['tree-node', 'clickable-leaf']"
          :node-title="'Click to view full text: ' + branch[1].text"
          @node-click="emit('selectNode', $event)"
          @add-to-chat="handleAddToChat($event, branchIndex)"
        />

        <!-- Expanded nodes (layer 2) -->
        <div v-if="isBranchExpanded(branchIndex)" class="expanded-nodes">
          <ArgumentNode
            v-for="(node, nodeIndex) in branch.slice(2, 4)"
            :key="node.id"
            :node="node"
            :max-text-length="50"
            :show-add-to-chat="true"
            add-to-chat-text="Add to chat"
            :node-classes="['tree-node', 'expanded-leaf']"
            :node-title="'Click to view full text: ' + node.text"
            @node-click="emit('selectNode', $event)"
            @add-to-chat="handleAddToChat($event, branchIndex)"
          />
        </div>
      </div>
    </div>

    <!-- Connection lines -->
    <TreeConnections
      :branches="branches"
      :expanded-branches="expandedBranches"
      :get-thesis-connection-start="getThesisConnectionStart"
      :get-branch-connection-end="getBranchConnectionEnd"
      :get-branch-color="getBranchColor"
    />
  </div>
</template>

<script setup lang="ts">
import ThesisNode from '../nodes/ThesisNode.vue'
import ArgumentNode from '../nodes/ArgumentNode.vue'
import TreeConnections from './TreeConnections.vue'
import type {
  ArgumentNode as ArgumentNodeType,
  BranchesData,
  AddToChatPayload,
} from '@/types/graph'

interface Props {
  thesisNode: ArgumentNodeType
  branches: BranchesData
  expandedBranches: Set<number>
  isBranchExpanded: (index: number) => boolean
  getBranchColor: (index: number) => string
  getThesisConnectionStart: () => { x: number; y: number }
  getBranchConnectionEnd: (index: number, totalBranches: number) => { x: number; y: number }
}

interface Emits {
  selectNode: [node: ArgumentNodeType]
  addToChat: [payload: AddToChatPayload]
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const handleAddToChat = (
  payloadOrNode: ArgumentNodeType | AddToChatPayload,
  branchIndex: number,
) => {
  // Accept either the new AddToChatPayload (emitted by ArgumentNode after refactor)
  // or the old node shape. Normalize and include branchIndex.
  let payload: AddToChatPayload
  if ((payloadOrNode as AddToChatPayload).text !== undefined) {
    payload = { ...(payloadOrNode as AddToChatPayload) }
  } else {
    const node = payloadOrNode as ArgumentNodeType
    payload = {
      text: node.text,
      nodeId: node.id,
      node,
      source: 'graph',
    }
  }
  emit('addToChat', payload)
}
</script>

<style scoped>
.tree-view {
  display: flex;
  flex-direction: column;
  min-height: 500px;
  position: relative;
  height: 100%;
}

.tree-thesis {
  display: flex;
  justify-content: center;
  margin-bottom: 30px;
  position: relative;
  z-index: 10;
  flex-shrink: 0;
}

.tree-branches {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 20px;
  justify-items: center;
  flex: 1;
  align-content: start;
  padding: 0 10px;
  position: relative;
  z-index: 5;
}

.branch-column {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 220px;
  width: 100%;
}

.branch-header {
  color: white;
  font-weight: bold;
  font-size: 12px;
  padding: 8px 16px;
  border-radius: 20px;
  margin-bottom: 20px;
  text-align: center;
  min-width: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.expanded-indicator {
  font-size: 14px;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

.expanded-nodes {
  margin-top: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
  width: 100%;
}

:deep(.tree-node) {
  margin-bottom: 15px;
  position: relative;
  z-index: 5;
  max-width: 180px;
  width: 100%;
  font-size: 12px;
  padding: 12px;
  transform: none !important;
  box-sizing: border-box;
}

:deep(.tree-node:hover) {
  transform: translateY(-3px) !important;
}

:deep(.clickable-leaf) {
  border: 3px solid #007bff !important;
  background: linear-gradient(135deg, #f8f9ff 0%, #e7f3ff 100%) !important;
  cursor: pointer;
  transition: all 0.3s ease;
}

:deep(.clickable-leaf:hover) {
  transform: translateY(-5px) scale(1.02) !important;
  box-shadow: 0 8px 25px rgba(0, 123, 255, 0.3) !important;
  border-color: #0056b3 !important;
}

:deep(.expanded-leaf) {
  border: 2px solid #28a745 !important;
  background: linear-gradient(135deg, #f8fff9 0%, #e7f7e7 100%) !important;
  cursor: pointer;
  transition: all 0.3s ease;
  opacity: 0;
  animation: slideInFade 0.5s ease-out forwards;
}

:deep(.expanded-leaf:hover) {
  transform: translateY(-3px) scale(1.01) !important;
  box-shadow: 0 6px 20px rgba(40, 167, 69, 0.3) !important;
  border-color: #1e7e34 !important;
}

:deep(.expanded-leaf .add-to-chat-hint) {
  background: rgba(40, 167, 69, 0.15);
  color: #28a745;
  border-color: rgba(40, 167, 69, 0.3);
}

:deep(.expanded-leaf:hover .add-to-chat-hint) {
  background: rgba(40, 167, 69, 0.25);
  color: #1e7e34;
  border-color: rgba(40, 167, 69, 0.5);
}

@keyframes slideInFade {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Responsive adjustments */
@media (max-width: 1200px) {
  .tree-branches {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 15px;
  }

  .branch-column {
    max-width: 180px;
  }

  :deep(.tree-node) {
    max-width: 160px;
    font-size: 11px;
    padding: 10px;
  }
}

@media (max-width: 900px) {
  .tree-branches {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
  }

  .branch-column {
    max-width: 160px;
  }

  :deep(.tree-node) {
    max-width: 140px;
    font-size: 10px;
    padding: 8px;
  }

  .tree-thesis {
    margin-bottom: 20px;
  }
}

@media (max-width: 768px) {
  .tree-view {
    min-height: 400px;
  }

  .tree-branches {
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 10px;
    padding: 0 5px;
  }

  .branch-header {
    font-size: 11px;
    padding: 6px 12px;
    min-width: 90px;
  }
}

@media (max-width: 480px) {
  .tree-branches {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }

  .branch-column {
    max-width: 140px;
  }

  :deep(.tree-node) {
    max-width: 120px;
    font-size: 9px;
    padding: 6px;
  }

  .branch-header {
    font-size: 10px;
    padding: 5px 10px;
    min-width: 80px;
  }
}
</style>
