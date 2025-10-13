<template>
  <div class="files-page">
    <!-- Navigation Header -->
    <div class="nav-header">
      <router-link to="/" class="back-button"> ← Back to Home </router-link>
      <h1 class="page-title">Files Management</h1>
      <div class="nav-spacer"></div>
    </div>

    <div class="container">
      <!-- Folder Breadcrumbs and Create Folder -->
      <section class="folder-bar">
        <div class="breadcrumbs">
          <span v-for="(crumb, idx) in breadcrumbs" :key="crumb.path">
            <a href="#" @click.prevent="changeFolder(crumb.path)">{{ crumb.name }}</a>
            <span v-if="idx < breadcrumbs.length - 1"> / </span>
          </span>
        </div>
        <div class="create-folder">
          <input v-model="newFolderName" placeholder="New folder name" />
          <button class="secondary-button" @click="createFolder">Create</button>
        </div>
      </section>

      <!-- Main content: upload (root-only) + combined folders/files grid -->
      <div class="content-area">
        <div v-if="loadError" class="error-banner">
          <div class="error-content">
            <strong>Error loading files:</strong>
            <span class="error-msg">{{ loadError }}</span>
            <button class="retry-button" @click="fetchFiles">Retry</button>
          </div>
        </div>

        <div class="page-description">
          <p>Upload and manage your discussion files</p>
        </div>

        <!-- Hidden global file input (always present) -->
        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".json,.pkl,.csv"
          @change="handleFileSelect"
          class="file-input"
        />

        <!-- Show the large drop-area only at root level -->
        <section class="upload-section" v-if="!currentFolder">
          <div
            class="upload-area"
            :class="{ 'drag-over': isDragOver }"
            @drop="handleDrop"
            @dragover.prevent
            @dragenter.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
          >
            <div class="upload-content">
              <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7,10 12,15 17,10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              <h3>Drop files here or click to upload</h3>
              <p>Supported formats: JSON, PKL, CSV</p>
              <button class="upload-button" @click="triggerFileSelect">Choose Files</button>
            </div>
          </div>
        </section>

        <!-- Files List (folders and files together) -->
        <section class="files-section">
          <div class="section-header">
            <h2>Available Files</h2>
            <div class="file-stats">
              <span>{{ files.length }} files</span>
              <span>{{ formatBytes(totalSize) }}</span>
            </div>
          </div>

          <div class="files-grid">
            <!-- Render folders first as file-like cards -->
            <template v-for="f in visibleFolders" :key="f">
              <div
                class="file-card folder-card"
                @click="changeFolder(currentFolder ? currentFolder + '/' + f : f)"
              >
                <div class="file-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M3 7v10a2 2 0 0 0 2 2h14" />
                    <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8" />
                  </svg>
                </div>
                <div class="file-info">
                  <h4 class="file-name">{{ f || 'root' }}</h4>
                  <p class="file-details"><span class="file-type">FOLDER</span></p>
                </div>
                <div class="file-actions">
                  <button
                    class="folder-menu-btn action-button"
                    @click.stop="toggleFolderMenu(f)"
                    :aria-expanded="menuOpenFor === f"
                    title="More"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <circle cx="5" cy="12" r="1.5" />
                      <circle cx="12" cy="12" r="1.5" />
                      <circle cx="19" cy="12" r="1.5" />
                    </svg>
                  </button>
                  <div v-if="menuOpenFor === f" class="folder-menu" @click.stop>
                    <button class="menu-item" @click.stop="onCreateSubfolder(f)">
                      Create subfolder
                    </button>
                    <button class="menu-item danger" @click.stop="onDeleteFolder(f)">
                      Delete folder
                    </button>
                  </div>
                </div>
              </div>
            </template>

            <!-- When inside a folder, show an Add-file card matching files' look -->
            <div v-if="currentFolder" class="file-card add-card" @click="triggerFileSelect">
              <div class="file-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <circle cx="12" cy="12" r="9" />
                  <line x1="12" y1="8" x2="12" y2="16" />
                  <line x1="8" y1="12" x2="16" y2="12" />
                </svg>
              </div>
              <div class="file-info">
                <h4 class="file-name">Add files</h4>
                <p class="file-details">Click to add files to this folder</p>
              </div>
            </div>

            <!-- Then render file cards -->
            <template v-for="file in files" :key="file.id">
              <div
                class="file-card"
                :class="{ selected: selectedFiles.includes(file.id) }"
                @click="toggleFileSelection(file.id)"
              >
                <div class="file-icon">
                  <svg
                    v-if="file.type === 'json'"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                  >
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14,2 14,8 20,8" />
                    <path d="M10 12a2 2 0 0 0 2 2c1.02 0 2-.98 2-2s-.98-2-2-2-2 .98-2 2z" />
                  </svg>
                  <svg
                    v-else-if="file.type === 'pkl'"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                  >
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14,2 14,8 20,8" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14,2 14,8 20,8" />
                  </svg>
                </div>
                <div class="file-info">
                  <h4 class="file-name">{{ file.name }}</h4>
                  <p class="file-details">
                    <span class="file-type">{{ file.type.toUpperCase() }}</span>
                    <span class="file-size">{{ formatBytes(file.size) }}</span>
                    <span class="file-date">{{ formatDate(file.uploadDate) }}</span>
                  </p>
                </div>
                <div class="file-actions">
                  <button class="action-button" @click.stop="previewFile(file)" title="Preview">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  </button>
                  <button class="action-button" @click.stop="downloadFile(file)" title="Download">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="7,10 12,15 17,10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                  </button>
                  <button
                    class="action-button delete"
                    @click.stop="deleteFile(file.id)"
                    title="Delete"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path d="M3 6h18" />
                      <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                      <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                    </svg>
                  </button>
                </div>
              </div>
            </template>

            <!-- If nothing to show, render empty-state -->
            <div v-if="visibleFolders.length === 0 && files.length === 0" class="empty-state">
              <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14,2 14,8 20,8" />
              </svg>
              <h3>No files uploaded yet</h3>
              <p>Upload your first discussion file to get started</p>
            </div>
          </div>
        </section>
      </div>
      <!-- Bulk Actions -->
      <section v-if="selectedFiles.length > 0" class="bulk-actions">
        <div class="selection-info">
          <span>{{ selectedFiles.length }} file(s) selected</span>
        </div>
        <div class="bulk-buttons">
          <button class="secondary-button" @click="clearSelection">Clear Selection</button>
          <button class="primary-button" @click="useSelectedFiles">Use in Discussion</button>
          <button class="danger-button" @click="deleteSelectedFiles">Delete Selected</button>
        </div>
      </section>
    </div>

    <!-- File Preview Modal -->
    <div v-if="previewModal.show" class="modal-overlay" @click="closePreview">
      <div class="modal-content preview-modal" @click.stop>
        <div class="modal-header">
          <h3>{{ previewModal.file?.name }}</h3>
          <button class="close-button" @click="closePreview">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <pre class="preview-content">{{ previewModal.content }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface FileItem {
  id: string
  name: string
  type: string
  size: number
  uploadDate: Date
  path?: string
  content?: any
}

const files = ref<FileItem[]>([])
const selectedFiles = ref<string[]>([])
const isDragOver = ref(false)
const fileInput = ref<HTMLInputElement>()
const previewModal = ref({
  show: false,
  file: null as FileItem | null,
  content: '',
})

const totalSize = computed(() => {
  return files.value.reduce((sum, file) => sum + file.size, 0)
})

const currentFolder = ref('') // '' means root
const folders = ref<string[]>([])
const allFolders = ref<string[]>([])

// compute folders visible under the currentFolder (immediate children)
const visibleFolders = computed(() => {
  const cur = (currentFolder.value || '').replace(/\\/g, '/')
  const prefix = cur ? cur + '/' : ''
  const children = new Set<string>()
  for (const f of allFolders.value) {
    const nf = f.replace(/\\/g, '/')
    if (nf === cur) continue
    if (!nf.startsWith(prefix)) continue
    const rem = nf.slice(prefix.length)
    const first = rem.split('/')[0]
    if (first) children.add(first)
  }
  return Array.from(children).sort()
})

const breadcrumbs = computed(() => {
  if (!currentFolder.value) return [{ name: 'root', path: '' }]
  const parts = currentFolder.value.split('/').filter(Boolean)
  const crumbs = [{ name: 'root', path: '' }]
  let acc = ''
  for (const p of parts) {
    acc = acc ? acc + '/' + p : p
    crumbs.push({ name: p, path: acc })
  }
  return crumbs
})

// Load existing files from backend via API
const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://127.0.0.1:8000'

const loadError = ref<string | null>(null)

async function fetchFiles() {
  loadError.value = null
  try {
    // request files for current folder
    const folderQuery = currentFolder.value
      ? `?folder=${encodeURIComponent(currentFolder.value)}`
      : ''
    const res = await fetch(`${API_BASE}/api/files${folderQuery}`)
    if (!res.ok) throw new Error(`Failed to list files (${res.status})`)
    const list = await res.json()
    files.value = list.map((f: any) => ({
      id: String(f.id ?? Math.random().toString(36).substr(2, 9)),
      name: f.name,
      type: f.type,
      size: f.size,
      uploadDate: new Date(f.uploadDate),
      path: f.path || f.name,
      content: null,
    }))
    // also fetch folders (full list) and compute visible children
    const resF = await fetch(`${API_BASE}/api/folders`)
    if (resF.ok) {
      const js = await resF.json()
      allFolders.value = js.folders || []
      folders.value = allFolders.value // keep for compatibility if other code uses it
    }
  } catch (err: any) {
    const msg = err?.message ?? String(err)
    console.error('Error loading existing files:', msg)
    loadError.value = msg
    files.value = []
  }
}

onMounted(() => {
  fetchFiles()
})

const triggerFileSelect = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) {
    handleFiles(Array.from(target.files))
  }
}

const handleDrop = (event: DragEvent) => {
  event.preventDefault()
  isDragOver.value = false

  if (event.dataTransfer?.files) {
    handleFiles(Array.from(event.dataTransfer.files))
  }
}

// Upload handler: send files to backend and add returned metadata to list
const handleFiles = (fileList: File[]) => {
  fileList.forEach(async (file) => {
    const form = new FormData()
    form.append('file', file)
    if (currentFolder.value) form.append('path', currentFolder.value)
    try {
      const res = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: form })
      if (!res.ok) throw new Error('Upload failed')
      const data = await res.json()
      files.value.push({
        id: String(data.file.id ?? Math.random().toString(36).substr(2, 9)),
        name: data.file.name,
        type: data.file.type,
        size: data.file.size,
        uploadDate: new Date(data.file.uploadDate),
        path: data.file.path || data.file.name,
        content: null,
      })
    } catch (err) {
      alert('Upload failed: ' + String(err))
    }
  })
}

const toggleFileSelection = (fileId: string) => {
  const index = selectedFiles.value.indexOf(fileId)
  if (index > -1) {
    selectedFiles.value.splice(index, 1)
  } else {
    selectedFiles.value.push(fileId)
  }
}

const clearSelection = () => {
  selectedFiles.value = []
}

const previewFile = (file: FileItem) => {
  previewModal.value = { show: true, file, content: 'Loading...' }
  ;(async () => {
    try {
      const path = file.path || file.name
      const res = await fetch(`${API_BASE}/api/files/${encodeURIComponent(path)}`)
      if (!res.ok) {
        previewModal.value.content = `Failed to load file: ${res.status}`
        return
      }
      // backend returns JSON for .json files, message for pkl, or file response
      const contentType = res.headers.get('content-type') || ''
      if (contentType.includes('application/json')) {
        const data = await res.json()
        previewModal.value.content = JSON.stringify(data, null, 2)
      } else {
        // try text
        const text = await res.text()
        previewModal.value.content = text
      }
    } catch (err) {
      console.error('Error fetching file preview:', err)
      previewModal.value.content = `Error: ${err instanceof Error ? err.message : String(err)}`
    }
  })()
}

const closePreview = () => {
  previewModal.value.show = false
}

const downloadFile = (file: FileItem) => {
  // Download via backend static endpoint
  const path = file.path || file.name
  const url = `${API_BASE}/api/files/${encodeURIComponent(path)}`
  // open in new tab to trigger download, the backend will set filename
  window.open(url, '_blank')
}

const deleteFile = (fileId: string) => {
  if (confirm('Are you sure you want to delete this file?')) {
    const file = files.value.find((f) => f.id === fileId)
    if (!file) return
    ;(async () => {
      try {
        // call path-based delete endpoint if available
        const target = file.path || file.name
        const res = await fetch(`${API_BASE}/api/files/${encodeURIComponent(target)}`, {
          method: 'DELETE',
        })
        if (!res.ok) throw new Error('Delete failed')
        files.value = files.value.filter((f) => f.id !== fileId)
        selectedFiles.value = selectedFiles.value.filter((id) => id !== fileId)
      } catch (err) {
        alert('Failed to delete file: ' + String(err))
      }
    })()
  }
}

// ...existing code...

const deleteSelectedFiles = () => {
  if (confirm(`Are you sure you want to delete ${selectedFiles.value.length} file(s)?`)) {
    ;(async () => {
      const ids = [...selectedFiles.value]
      for (const id of ids) {
        try {
          const file = files.value.find((f) => f.id === id)
          const target = file?.path || file?.name || id
          const res = await fetch(`${API_BASE}/api/files/${encodeURIComponent(target)}`, {
            method: 'DELETE',
          })
          if (!res.ok) throw new Error('Delete failed')
          files.value = files.value.filter((f) => f.id !== id)
          selectedFiles.value = selectedFiles.value.filter((i) => i !== id)
        } catch (err) {
          alert('Failed to delete file id=' + id + ': ' + String(err))
        }
      }
    })()
  }
}

const changeFolder = (path: string) => {
  currentFolder.value = path
  fetchFiles()
}

const newFolderName = ref('')
const createFolder = async () => {
  if (!newFolderName.value) return
  const target = currentFolder.value
    ? currentFolder.value + '/' + newFolderName.value
    : newFolderName.value
  try {
    const res = await fetch(`${API_BASE}/api/folders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: target }),
    })
    if (!res.ok) throw new Error('Create folder failed')
    newFolderName.value = ''
    await fetchFiles()
  } catch (err) {
    alert('Failed to create folder: ' + String(err))
  }
}

const onDeleteFolder = async (folderName: string) => {
  const target = currentFolder.value ? currentFolder.value + '/' + folderName : folderName
  if (!confirm(`Delete folder '${target}' and all its contents? This cannot be undone.`)) return
  try {
    const res = await fetch(`${API_BASE}/api/folders/${encodeURIComponent(target)}`, {
      method: 'DELETE',
    })
    if (!res.ok) throw new Error('Delete failed')
    // refresh folders and files
    await fetchFiles()
  } catch (err) {
    alert('Failed to delete folder: ' + String(err))
  }
}

const menuOpenFor = ref<string | null>(null)

const toggleFolderMenu = (folderName: string) => {
  menuOpenFor.value = menuOpenFor.value === folderName ? null : folderName
}

const onCreateSubfolder = async (folderName: string) => {
  const sub = prompt('Subfolder name:')
  if (!sub) return
  const target = currentFolder.value
    ? currentFolder.value + '/' + folderName + '/' + sub
    : folderName + '/' + sub
  try {
    const res = await fetch(`${API_BASE}/api/folders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: target }),
    })
    if (!res.ok) throw new Error('Create subfolder failed')
    await fetchFiles()
    menuOpenFor.value = null
  } catch (err) {
    alert('Failed to create subfolder: ' + String(err))
  }
}

const useSelectedFiles = () => {
  // Navigate to discussion page with selected files (pass first selected file name as query)
  if (selectedFiles.value.length === 0) {
    router.push('/discussion')
    return
  }
  const firstId = selectedFiles.value[0]
  const file = files.value.find((f) => f.id === firstId)
  if (file) {
    router.push({ path: '/discussion', query: { file: file.name } })
  } else {
    router.push('/discussion')
  }
}

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (date: Date) => {
  return (
    date.toLocaleDateString() +
    ' ' +
    date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  )
}
</script>

<style scoped>
.files-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  overflow-y: auto !important;
  box-sizing: border-box;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.container {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 2rem;
  flex: 1;
  overflow-y: auto;
  box-sizing: border-box;
}

.content-grid {
  /* removed two-column layout: folders are rendered inline with files now */
  display: block;
}

.nav-header {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  min-height: 60px;
  box-sizing: border-box;
}

.back-button {
  color: #6c757d;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.back-button:hover {
  background: #e9ecef;
  color: #495057;
}

.page-title {
  flex: 1;
  text-align: center;
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #495057;
}

.nav-spacer {
  width: 120px; /* Same width as back button to center the title */
}

.page-header {
  text-align: center;
  margin-bottom: 3rem;
}

.page-header h1 {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.page-header p {
  font-size: 1.1rem;
  color: #7f8c8d;
}

.page-description {
  text-align: center;
  margin: 2rem 0;
}

.page-description p {
  font-size: 1.1rem;
  color: #7f8c8d;
  margin: 0;
}

.upload-section {
  margin-bottom: 3rem;
}

.main-column {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.folder-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.breadcrumbs a {
  color: #3498db;
  text-decoration: none;
  font-weight: 600;
}

.create-folder {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.create-folder input {
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  border: 1px solid #dfe6e9;
  min-width: 180px;
}

.folder-card {
  /* folder items reuse file-card look when rendered inline */
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.18s ease;
  cursor: pointer;
}

.folder-card .file-icon svg {
  color: #f39c12;
}

.add-card {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.add-card .file-icon svg {
  width: 3rem;
  height: 3rem;
  color: #3498db;
}

.folder-card {
  background: white;
  border-radius: 10px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition:
    transform 0.12s ease,
    box-shadow 0.12s ease;
  border: 1px solid transparent;
  min-height: 110px;
  text-align: center;
}

.folder-menu-btn {
  background: transparent;
  border: 1px solid transparent;
  padding: 6px;
  border-radius: 6px;
  cursor: pointer;
  color: #7f8c8d;
}

.folder-menu-btn svg {
  width: 0.95rem;
  height: 0.95rem;
}

.folder-menu {
  position: absolute;
  top: 36px;
  right: 6px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
  border: 1px solid #e9ecef;
  display: flex;
  flex-direction: column;
  z-index: 30;
}

.folder-menu .menu-item {
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: none;
  text-align: left;
  cursor: pointer;
}

.folder-menu .menu-item:hover {
  background: #f6f8fa;
}

.folder-menu .menu-item.danger {
  color: #e74c3c;
}

.folder-card svg {
  margin: 0;
}

.folder-name {
  font-weight: 600;
  color: #2c3e50;
  max-width: 100%;
  overflow-wrap: anywhere;
  white-space: normal;
  font-size: 0.95rem;
}

.upload-area {
  border: 2px dashed #bdc3c7;
  border-radius: 12px;
  padding: 3rem;
  text-align: center;
  background: rgba(255, 255, 255, 0.8);
  transition: all 0.3s ease;
  cursor: pointer;
}

.upload-area:hover,
.upload-area.drag-over {
  border-color: #3498db;
  background: rgba(52, 152, 219, 0.1);
}

.upload-content {
  max-width: 400px;
  margin: 0 auto;
}

.upload-icon {
  width: 4rem;
  height: 4rem;
  color: #3498db;
  margin-bottom: 1rem;
}

.upload-content h3 {
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.upload-content p {
  color: #7f8c8d;
  margin-bottom: 1.5rem;
}

.file-input {
  display: none;
}

.upload-button {
  background: #3498db;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.3s ease;
}

.upload-button:hover {
  background: #2980b9;
}

.files-section {
  margin-bottom: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  color: #2c3e50;
  margin: 0;
}

.file-stats {
  display: flex;
  gap: 1rem;
  color: #7f8c8d;
  font-size: 0.9rem;
}

.files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.25rem;
  width: 100%;
}

.file-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  cursor: pointer;
  border: 2px solid transparent;
}

.file-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.file-card.selected {
  border-color: #3498db;
  background: rgba(52, 152, 219, 0.05);
}

.file-icon {
  width: 3rem;
  height: 3rem;
  color: #3498db;
  margin-bottom: 1rem;
}

.file-icon svg {
  width: 100%;
  height: 100%;
}

.file-name {
  font-size: 1.1rem;
  color: #2c3e50;
  margin: 0 0 0.5rem 0;
  word-break: break-word;
}

.file-details {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin: 0 0 1rem 0;
  color: #7f8c8d;
  font-size: 0.85rem;
}

.file-type {
  background: #ecf0f1;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-weight: 500;
}

.file-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.action-button {
  background: none;
  border: 1px solid #bdc3c7;
  border-radius: 6px;
  padding: 0.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  color: #7f8c8d;
}

.action-button:hover {
  background: #ecf0f1;
  border-color: #95a5a6;
}

.action-button.delete:hover {
  background: #e74c3c;
  border-color: #e74c3c;
  color: white;
}

.action-button svg {
  width: 1rem;
  height: 1rem;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #7f8c8d;
}

.empty-icon {
  width: 4rem;
  height: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.bulk-actions {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.selection-info {
  color: #2c3e50;
  font-weight: 500;
}

.bulk-buttons {
  display: flex;
  gap: 1rem;
}

.secondary-button,
.primary-button,
.danger-button {
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.secondary-button {
  background: #ecf0f1;
  color: #2c3e50;
}

.secondary-button:hover {
  background: #d5dbdb;
}

.primary-button {
  background: #3498db;
  color: white;
}

.primary-button:hover {
  background: #2980b9;
}

.danger-button {
  background: #e74c3c;
  color: white;
}

.danger-button:hover {
  background: #c0392b;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 90vw;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.preview-modal {
  width: 800px;
}

.modal-header {
  padding: 1.5rem;
  border-bottom: 1px solid #ecf0f1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  color: #2c3e50;
}

.close-button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  color: #7f8c8d;
  border-radius: 4px;
  transition: background 0.3s ease;
}

.close-button:hover {
  background: #ecf0f1;
}

.close-button svg {
  width: 1.25rem;
  height: 1.25rem;
}

.modal-body {
  padding: 1.5rem;
  max-height: 60vh;
  overflow-y: auto;
}

.preview-content {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 0.85rem;
  line-height: 1.4;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
}

@media (max-width: 768px) {
  .container {
    padding: 1rem;
  }

  .nav-header {
    padding: 0.75rem 1rem;
    min-height: 50px;
  }

  .page-title {
    font-size: 1.1rem;
  }

  .nav-spacer {
    width: 80px;
  }

  .page-description {
    margin: 1.5rem 0;
  }

  .content-grid {
    grid-template-columns: 1fr;
  }

  .files-grid {
    grid-template-columns: 1fr;
  }

  .bulk-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .bulk-buttons {
    justify-content: stretch;
  }

  .bulk-buttons button {
    flex: 1;
  }

  .preview-modal {
    width: 95vw;
  }
}
</style>
