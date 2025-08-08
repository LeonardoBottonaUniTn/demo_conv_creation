// Composable for managing graph data and state
import { ref, computed, type Ref } from 'vue'
import type { ArgumentNode, BranchesData, Position } from '../types/graph'
import discussionData from '../backend/Can_Man-made_Climate_Change_Be_Reversed_20each.json'

export function useGraphData() {
  const discussionBranches = ref<BranchesData>([])
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
      discussionBranches.value = discussionData as BranchesData
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
