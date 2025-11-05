// Composable for managing graph data and state
import { ref, computed } from 'vue'
import type { ArgumentNode, BranchesData } from '../types/graph'

const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

// keep the original discussion object returned by the backend
const discussionRoot = ref<any>(null)

export function useGraphData() {
  const discussionBranches = ref<BranchesData>([])
  const selectedBranch = ref(0)
  const loading = ref(true)
  const error = ref('')
  const expandedBranches = ref<Set<number>>(new Set())

  const currentBranchNodes = computed(() => {
    return discussionBranches.value[selectedBranch.value] || []
  })

  const loadDiscussionData = async (filename?: string) => {
    try {
      loading.value = true
      // fetch discussion from backend API
      const res = filename
        ? await fetch(`${API_BASE}/api/files/${encodeURIComponent(filename)}`)
        : await fetch(`${API_BASE}/api/discussion`)
      if (!res.ok) throw new Error(`Failed to load discussion: ${res.status}`)
      const data = await res.json()
      // Expecting { users: [...], tree: {...} }
      discussionRoot.value = data.tree
      // preserve previous behaviour: collect root-to-leaf branches
      loading.value = false
    } catch (err) {
      console.error('Error loading discussion data:', err)
      error.value = 'Failed to load discussion data'
      loading.value = false
    }
  }

  // Find a node in the original discussion tree by id
  function findNodeById(id: string, node: any = discussionRoot.value): any | null {
    if (!node) return null
    if (node.id === id) return node
    if (!node.children) return null
    for (const child of node.children) {
      const found = findNodeById(id, child)
      if (found) return found
    }
    return null
  }

  // Build a nested chain (one-child-per-level) from the branch array so D3 can render it as a tree-like object
  function getBranchChain(branchIndex: number) {
    const branch = discussionBranches.value[branchIndex]
    if (!branch || branch.length === 0) return null
    // For each id in the branch, find the original node and clone it shallowly
    const clones = branch.map((b: any) => {
      const orig = findNodeById(b.id)
      // prefer original node if present, otherwise use the simplified b
      const source = orig || b
      // shallow clone to avoid mutating original
      const cloned: any = { ...source }
      cloned.children = []
      return cloned
    })
    // link the clones sequentially
    for (let i = 0; i < clones.length - 1; i++) {
      clones[i].children = [clones[i + 1]]
    }
    return clones[0]
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
    loadDiscussionData,
    discussionRoot,
    getBranchChain,
    expandBranch,
    isBranchExpanded,
  }
}
