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
      let res: Response
      if (filename) {
        // use encodeURI so that folder separators ('/') are preserved for path parameters
        const tryUrl = `${API_BASE}/api/files/${encodeURI(filename)}`
        console.debug('[useGraphData] requesting discussion file URL:', tryUrl)
        res = await fetch(tryUrl)

        // If backend couldn't find the provided path, try the basename as a fallback
        if (!res.ok && res.status === 404) {
          const base = filename.split('/').pop() || filename
          if (base !== filename) {
            const tryBaseUrl = `${API_BASE}/api/files/${encodeURI(base)}`
            console.debug('[useGraphData] fallback to basename URL:', tryBaseUrl)
            res = await fetch(tryBaseUrl)
          }
        }

        // Additional fallback: if still 404, try to find file metadata and fetch by numeric id
        if (!res.ok && res.status === 404) {
          try {
            console.debug('[useGraphData] attempting DB lookup for', filename)
            const listRes = await fetch(`${API_BASE}/api/files`)
            if (listRes.ok) {
              const list = await listRes.json()
              const normalizedTarget = String(filename).replace(/^files_root[\\/]/, '')
              let matched: any = null
              for (const f of list) {
                const rawPath = f.path || f.name
                const norm = String(rawPath).replace(/^files_root[\\/]/, '')
                if (
                  norm === normalizedTarget ||
                  f.name === filename ||
                  f.name === normalizedTarget
                ) {
                  matched = f
                  break
                }
              }
              if (matched && matched.id) {
                console.debug('[useGraphData] found DB record, fetching by id:', matched.id)
                res = await fetch(`${API_BASE}/api/files/id/${matched.id}`)
              }
            }
          } catch (e) {
            console.debug('[useGraphData] DB lookup fallback failed', e)
          }
        }
      } else {
        // No filename provided: do not attempt legacy `/api/discussion` (server doesn't expose it).
        // Clear previous data and return early so callers can prompt the user to choose a file.
        discussionRoot.value = null
        loading.value = false
        error.value = ''
        return
      }
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
