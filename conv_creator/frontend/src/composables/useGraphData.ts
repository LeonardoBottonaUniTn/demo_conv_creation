// Composable for managing graph data and state
import { ref, computed, type Ref } from 'vue'
import type { ArgumentNode, BranchesData, Position } from '../types/graph'
import discussionData from 'backend/bp_130_0_d3.json'

export function useGraphData() {
  // Helper: traverse tree and collect all branches (root-to-leaf paths)
  function collectBranches(
    node: any,
    path: ArgumentNode[] = [],
    branches: ArgumentNode[][] = [],
  ): ArgumentNode[][] {
    const currentNode: ArgumentNode = {
      id: node.id,
      type: node.type ?? 'thesis',
      text: node.text,
    }
    const newPath = [...path, currentNode]
    if (!node.children || node.children.length === 0) {
      branches.push(newPath)
    } else {
      for (const child of node.children) {
        collectBranches(child, newPath, branches)
      }
    }
    return branches
  }

  const discussionBranches = ref<BranchesData>(collectBranches(discussionData))
  const selectedBranch = ref(0)
  const loading = ref(true)
  const error = ref('')
  const expandedBranches = ref<Set<number>>(new Set())

  const currentBranchNodes = computed(() => {
    return discussionBranches.value[selectedBranch.value] || []
  })

  const thesisNode = computed(() => {
    return (
      discussionBranches.value[0]?.[0] || { id: '1', type: 'thesis' as const, text: 'Main Thesis' }
    )
  })

  const loadDiscussionData = async () => {
    try {
      loading.value = true
      discussionBranches.value = collectBranches(discussionData)
      loading.value = false
    } catch (err) {
      console.error('Error loading discussion data:', err)
      error.value = 'Failed to load discussion data'
      loading.value = false
    }
  }

  const expandBranch = (branchIndex: number) => {
    expandedBranches.value.add(branchIndex)
  }

  const isBranchExpanded = (branchIndex: number) => {
    return expandedBranches.value.has(branchIndex)
  }

  return {
    discussionBranches,
    selectedBranch,
    loading,
    error,
    expandedBranches,
    currentBranchNodes,
    thesisNode,
    loadDiscussionData,
    expandBranch,
    isBranchExpanded,
  }
}
