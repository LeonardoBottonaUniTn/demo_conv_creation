import { ref, computed } from 'vue'
import type { ArgumentNode, BranchesData } from '../types/graph'

export function useGraphVisualization(discussionBranches: BranchesData, thesisNode: ArgumentNode) {
  // Selected node state
  const selectedNode = ref<ArgumentNode | null>(null)

  // Expanded branches state
  const expandedBranches = ref<string[]>([])

  // Select a node
  function selectNode(node: ArgumentNode) {
    selectedNode.value = node
  }

  // Close modal
  function closeModal() {
    selectedNode.value = null
  }

  // Branch expansion logic
  function isBranchExpanded(branchId: string) {
    return expandedBranches.value.includes(branchId)
  }
  function getSingleBranchPosition(index: number) {
    return {
      position: 'absolute',
      left: '50%',
      transform: 'translateX(-50%)',
      top: `${index * 120}px`, // Adjust vertical spacing as needed
    }
  }

  function toggleBranch(branchId: string) {
    if (isBranchExpanded(branchId)) {
      expandedBranches.value = expandedBranches.value.filter((id) => id !== branchId)
    } else {
      expandedBranches.value.push(branchId)
    }
  }

  // Color assignment (example logic)
  function getBranchColor(branchId: string) {
    // Simple hash for color assignment
    const colors = ['#3498db', '#e67e22', '#2ecc71', '#9b59b6', '#e74c3c']
    let hash = 0
    for (let i = 0; i < branchId.length; i++) {
      hash += branchId.charCodeAt(i)
    }
    return colors[hash % colors.length]
  }

  // Connection calculations (stub)
  function getThesisConnectionStart() {
    // Implement actual logic as needed
    return { x: 0, y: 0 }
  }

  function getBranchConnectionEnd(branchId: string) {
    // Implement actual logic as needed
    return { x: 0, y: 0 }
  }

  return {
    selectedNode,
    selectNode,
    closeModal,
    expandedBranches,
    isBranchExpanded,
    toggleBranch,
    getBranchColor,
    getThesisConnectionStart,
    getBranchConnectionEnd,
    getSingleBranchPosition,
  }
}
