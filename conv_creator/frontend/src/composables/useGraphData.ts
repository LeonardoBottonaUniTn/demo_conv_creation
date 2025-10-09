// Composable for managing graph data and state
import { ref, computed } from 'vue'
import type { ArgumentNode, BranchesData } from '../types/graph'

const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

let discussionData: any = null

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
      // fetch discussion from backend API
      const res = await fetch(`${API_BASE}/api/discussion`)
      if (!res.ok) throw new Error(`Failed to load discussion: ${res.status}`)
      discussionData = await res.json()
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
