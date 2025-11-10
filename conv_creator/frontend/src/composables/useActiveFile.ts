import { ref } from 'vue'

/**
 * Shared composable to provide the currently active file reference
 * and its parsed content across components.
 *
 * Usage:
 * const { activeFile, fileContent, loadFile } = useActiveFile()
 */
export function useActiveFile() {
  const activeFile = ref<string | undefined>(undefined)
  const fileContent = ref<any>(null)

  const apiBase = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

  async function loadFile(fileRef?: string) {
    if (!fileRef) return null
    try {
      // remember which file is active
      activeFile.value = fileRef
      const res = await fetch(`${apiBase}/api/files/${fileRef}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!res.ok) {
        const txt = await res.text()
        throw new Error(txt || `HTTP ${res.status}`)
      }
      fileContent.value = await res.json()
      return fileContent.value
    } catch (e) {
      console.error('[useActiveFile] failed to load file', fileRef, e)
      // keep previous fileContent if fetch fails; return null to indicate failure
      return null
    }
  }

  // Ensure-loaded helper: dedupe concurrent loads for the same fileRef.
  const inFlight = new Map<string, Promise<any> | null>()

  function ensureLoaded(fileRef?: string) {
    if (!fileRef) return Promise.resolve(null)
    // if already loaded and matches requested file, resolve with cached content
    if (fileContent.value && activeFile.value === fileRef) return Promise.resolve(fileContent.value)
    const existing = inFlight.get(fileRef)
    if (existing) return existing
    const p = (async () => {
      try {
        const result = await loadFile(fileRef)
        return result
      } finally {
        // clear in-flight entry so subsequent calls can retry if needed
        inFlight.delete(fileRef)
      }
    })()
    inFlight.set(fileRef, p)
    return p
  }

  return {
    activeFile,
    fileContent,
    loadFile,
    ensureLoaded,
  }
}
