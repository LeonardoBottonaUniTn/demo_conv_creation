<template>
  <div class="files-page">
    <!-- Navigation Header -->
    <div class="nav-header">
      <router-link to="/" class="back-button"> ← Back to Home </router-link>
      <h1 class="page-title">Files Management</h1>
      <div class="nav-spacer"></div>
    </div>

    <div class="container">
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
                :class="{ 'drop-target': hoverFolder === f }"
                @click="changeFolder(currentFolder ? currentFolder + '/' + f : f)"
                @dragover.prevent
                @dragenter.prevent="onFolderDragEnter(f)"
                @dragleave="onFolderDragLeave(f)"
                @drop.prevent="onDropOnFolder(f, $event)"
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
                :class="{
                  selected: selectedFiles.includes(file.id),
                  dragging: draggingId === file.id,
                }"
                style="position: relative"
                @click="toggleFileSelection(file.id)"
                draggable="true"
                @dragstart="onDragStart(file, $event)"
                @dragend="onDragEnd"
              >
                <!-- Overlay in top-right: show warning for invalid files, otherwise show category label when structure is OK -->
                <div
                  class="structure-overlay"
                  v-if="file.structureOk === 0"
                  title="Structure warning"
                >
                  <button
                    class="structure-banner"
                    @click.stop.prevent="openStructureWarning(file)"
                    aria-label="Open structure warning"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      width="16"
                      height="16"
                      fill="none"
                      stroke="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
                      ></path>
                      <line x1="12" y1="9" x2="12" y2="13"></line>
                      <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                    <span>Structure warning</span>
                  </button>
                </div>

                <div
                  class="structure-overlay"
                  v-else-if="file.structureOk === 1"
                  :title="
                    file.category
                      ? file.category === 'discussion'
                        ? 'Discussion tree'
                        : file.category === 'draft'
                          ? 'Draft file'
                          : file.category
                      : 'Valid file'
                  "
                >
                  <div
                    class="category-badge"
                    :class="file.category ? file.category.toLowerCase() : 'unknown'"
                  >
                    {{
                      file.category === 'discussion'
                        ? 'Discussion'
                        : file.category === 'draft'
                          ? 'Draft'
                          : file.category || 'File'
                    }}
                  </div>
                </div>
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
                  <button class="action-button" @click.stop="useFile(file)" title="Use in Discussion">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
                    </svg>
                  </button>
                  <button class="action-button" @click.stop="previewFile(file)" title="Preview">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
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

          <button class="secondary-button" @click="downloadSelectedFiles">Download</button>
          <button class="secondary-button" @click="openMoveModalForSelected">Move</button>
          <button class="danger-button" @click="deleteSelectedFiles">Delete Selected</button>
        </div>
      </section>
      <!-- Move modal -->
      <div v-if="moveModal.show" class="modal-overlay" @click="closeMoveModal">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h3>Move file(s)</h3>
            <button class="close-button" @click="closeMoveModal">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
          <div class="modal-body">
            <p>Select destination folder:</p>
            <select
              v-model="moveModal.dest"
              style="width: 100%; padding: 0.5rem; border-radius: 6px; border: 1px solid #dfe6e9"
            >
              <option :value="''">root</option>
              <option v-for="f in allFolders" :key="f" :value="f">{{ f }}</option>
            </select>
            <div style="margin-top: 1rem; display: flex; gap: 0.5rem; justify-content: flex-end">
              <button class="secondary-button" @click="closeMoveModal">Cancel</button>
              <button class="primary-button" @click.prevent="() => moveFiles()">Move</button>
            </div>
            <p
              v-if="moveModal.targets.length"
              style="margin-top: 1rem; color: #7f8c8d; font-size: 0.9rem"
            >
              Moving {{ moveModal.targets.length }} item(s)
            </p>
          </div>
        </div>
      </div>
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

    <!-- Structure Warning Modal -->
    <div v-if="warningModal.show" class="modal-overlay" @click="closeWarning">
      <div class="modal-content warning-modal" @click.stop>
        <div class="modal-header">
          <h3>Structure issues — {{ warningModal.file?.name }}</h3>
          <button class="close-button" @click="closeWarning">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <p>The file does not conform to the expected discussion structure. Issues found:</p>
          <ul class="issue-list">
            <li v-for="(iss, i) in warningModal.issues" :key="i">{{ iss }}</li>
          </ul>
          <details style="margin-top: 1rem">
            <summary>Preview (truncated)</summary>
            <pre class="preview-content">{{ warningModal.preview }}</pre>
          </details>
          <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1rem">
            <button class="secondary-button" @click="closeWarning">Close</button>
            <button
              class="primary-button"
              @click="attemptFix"
              title="Try to auto-fix the file structure using AI"
            >
              Attempt fix
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Fix Preview Modal -->
    <div v-if="fixPreviewModal.show" class="modal-overlay" @click="closeFixPreview">
      <div
        class="modal-content fix-preview-modal"
        @click.stop
        style="max-width: 90vw; width: 1200px"
      >
        <div class="modal-header">
          <h3>AI Suggested Fix — {{ fixPreviewModal.file?.name }}</h3>
          <button class="close-button" @click="closeFixPreview">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div v-if="fixPreviewModal.loading" style="text-align: center; padding: 2rem">
            <p>Generating fix with AI...</p>
            <p style="color: #7f8c8d; font-size: 0.9rem; margin-top: 0.5rem">
              This may take a few seconds
            </p>
          </div>
          <div v-else style="display: flex; gap: 1rem; height: 60vh">
            <!-- Original -->
            <div style="flex: 1; display: flex; flex-direction: column">
              <h4 style="margin: 0 0 0.5rem 0; color: #e74c3c">
                Original ({{
                  Array.isArray(fixPreviewModal.original) ? fixPreviewModal.original.length : 0
                }}
                items)
              </h4>
              <div
                style="
                  flex: 1;
                  overflow: auto;
                  background: #f8f9fa;
                  border: 1px solid #ddd;
                  border-radius: 4px;
                  padding: 1rem;
                "
              >
                <pre style="margin: 0; font-size: 0.85rem; white-space: pre-wrap">{{
                  JSON.stringify(fixPreviewModal.original, null, 2)
                }}</pre>
              </div>
            </div>
            <!-- Fixed -->
            <div style="flex: 1; display: flex; flex-direction: column">
              <h4 style="margin: 0 0 0.5rem 0; color: #27ae60">
                Fixed ({{ Array.isArray(fixPreviewModal.fixed) ? fixPreviewModal.fixed.length : 0 }}
                items)
              </h4>
              <div
                style="
                  flex: 1;
                  overflow: auto;
                  background: #f8f9fa;
                  border: 1px solid #ddd;
                  border-radius: 4px;
                  padding: 1rem;
                "
              >
                <pre style="margin: 0; font-size: 0.85rem; white-space: pre-wrap">{{
                  JSON.stringify(fixPreviewModal.fixed, null, 2)
                }}</pre>
              </div>
            </div>
          </div>
          <div
            v-if="!fixPreviewModal.loading"
            style="
              display: flex;
              gap: 0.5rem;
              justify-content: flex-end;
              margin-top: 1rem;
              padding-top: 1rem;
              border-top: 1px solid #ddd;
            "
          >
            <button class="secondary-button" @click="closeFixPreview">Cancel</button>
            <button
              class="primary-button"
              @click="applyFix"
              style="background: #27ae60"
              title="Apply this fix and save the file (a backup will be created)"
            >
              Apply Fix
            </button>
          </div>
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
  structureOk?: number | null
  category?: string | null
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

// Warning modal for structure issues
const warningModal = ref({
  show: false,
  file: null as FileItem | null,
  issues: [] as string[],
  preview: '',
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
    files.value = list.map((f: any) => {
      // normalize stored path: older DB rows may contain a 'files_root/...' prefix
      const rawPath = f.path || f.name
      const normalizedPath = String(rawPath).replace(/^files_root[\/]/, '')
      return {
        id: String(f.id ?? Math.random().toString(36).substr(2, 9)),
        name: f.name,
        type: f.type,
        size: f.size,
        uploadDate: new Date(f.uploadDate),
        path: normalizedPath,
        content: null,
        structureOk: typeof f.structure_ok !== 'undefined' ? f.structure_ok : null,
        category: typeof f.category !== 'undefined' ? f.category : null,
      }
    })
    // If we're at root, show only top-level files (those not living in subfolders).
    // If we're inside a folder, show only immediate children of that folder
    // (do not include files that live in nested subfolders). The backend may
    // return files recursively; enforce a client-side boundary here to avoid
    // duplicate appearances of the same file both in parent and child folder.
    const normalizeRel = (p: string) => p.replace(/^files_root\//, '')
    if (!currentFolder.value) {
      files.value = files.value.filter((fi) => {
        const p = (fi.path || fi.name) as string
        const rel = normalizeRel(p)
        return !rel.includes('/')
      })
    } else {
      const cur = currentFolder.value.replace(/^\/|\/$/g, '')
      const prefix = cur + '/'
      files.value = files.value.filter((fi) => {
        const p = (fi.path || fi.name) as string
        const rel = normalizeRel(p)
        // must live inside the folder
        if (!rel.startsWith(prefix)) return false
        // drop the folder prefix and ensure there's no further '/'
        const rem = rel.slice(prefix.length)
        return !rem.includes('/')
      })
    }
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
        structureOk: typeof data.file.structure_ok !== 'undefined' ? data.file.structure_ok : null,
        category: typeof data.file.category !== 'undefined' ? data.file.category : null,
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
      console.log('Fetching preview for file', file)

      const url = getFileApiUrl(file, 'get')
      const res = await fetch(url)
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

// Helper: build API URL for a file, prefer id-based endpoints when id is numeric
function getFileApiUrl(file: FileItem, action: 'get' | 'delete' | 'download' = 'get') {
  // if id looks numeric, prefer id-based route
  const idStr = String(file.id ?? '')
  const isNumericId = /^[0-9]+$/.test(idStr)
  const query = action === 'download' ? '?download=true' : ''
  if (isNumericId) {
    // for get/download we reuse the same id endpoint; delete has its own id route too
    return `${API_BASE}/api/files/id/${idStr}${query}`
  }
  const path = file.path || file.name
  return `${API_BASE}/api/files/${encodeURIComponent(path)}${query}`
}

// Client-side structure checker (mirrors backend rules) — returns array of issue messages
function checkStructure(data: any): string[] {
  const issues: string[] = []

  function checkNode(node: any, path: string) {
    if (typeof node !== 'object' || node === null || Array.isArray(node)) {
      issues.push(`${path}: node is not an object`)
      return
    }
    const required = ['id', 'speaker', 'text', 'children']
    for (const k of required) {
      if (!(k in node)) issues.push(`${path}: missing required key '${k}'`)
    }
    if ('id' in node && typeof node.id !== 'string') issues.push(`${path}.id: expected string`)
    if ('speaker' in node && typeof node.speaker !== 'string')
      issues.push(`${path}.speaker: expected string`)
    if ('text' in node && typeof node.text !== 'string')
      issues.push(`${path}.text: expected string`)
    if ('children' in node) {
      if (!Array.isArray(node.children)) {
        issues.push(`${path}.children: expected array`)
      } else {
        node.children.forEach((ch: any, idx: number) => checkNode(ch, `${path}.children[${idx}]`))
      }
    }
  }

  if (Array.isArray(data)) {
    data.forEach((el, i) => checkNode(el, `root[${i}]`))
  } else {
    checkNode(data, 'root')
  }
  return issues
}

async function openStructureWarning(file: FileItem) {
  warningModal.value = { show: true, file, issues: [], preview: '' }
  try {
    const url = getFileApiUrl(file, 'get')
    const res = await fetch(url)
    if (!res.ok) {
      warningModal.value.issues = [`Failed to fetch file: ${res.status}`]
      return
    }
    const contentType = res.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const data = await res.json()
      // run client-side checker
      const issues = checkStructure(data)
      warningModal.value.issues = issues.length ? issues : ['Unknown structural issue']
      // also keep a small preview
      warningModal.value.preview = JSON.stringify(data, null, 2).slice(0, 2000)
    } else {
      const text = await res.text()
      warningModal.value.issues = ['File is not JSON — cannot analyze structure']
      warningModal.value.preview = text.slice(0, 2000)
    }
  } catch (err: any) {
    warningModal.value.issues = [String(err?.message ?? err)]
  }
}

const closePreview = () => {
  previewModal.value.show = false
}

const closeWarning = () => {
  warningModal.value.show = false
}

// Store the preview of the fix
const fixPreviewModal = ref({
  show: false,
  file: null as FileItem | null,
  original: null as any,
  fixed: null as any,
  loading: false,
})

const attemptFix = async () => {
  const file = warningModal.value.file
  if (!file) return

  try {
    // Show loading state
    fixPreviewModal.value.loading = true
    fixPreviewModal.value.file = file
    fixPreviewModal.value.show = true

    // Request a preview of the fix
    const response = await fetch(`http://localhost:8000/api/files/fix/${file.id}/preview`, {
      method: 'POST',
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Fix preview failed')
    }

    const result = await response.json()

    // Store the preview data
    fixPreviewModal.value.original = result.original
    fixPreviewModal.value.fixed = result.fixed
    fixPreviewModal.value.loading = false

    // Close the warning modal
    closeWarning()
  } catch (error) {
    console.error('Fix preview failed:', error)
    fixPreviewModal.value.show = false
    fixPreviewModal.value.loading = false
    alert(`Failed to preview fix:\n\n${error instanceof Error ? error.message : String(error)}`)
  }
}

const applyFix = async () => {
  const file = fixPreviewModal.value.file
  const fixedData = fixPreviewModal.value.fixed

  if (!file || !fixedData) return

  // Ask user if they want to keep the original file
  const keepOriginal = confirm(
    `Do you want to keep the original file?\n\n` +
      `OK = Keep original and create a _fix version.\nCancel = Overwrite the original file.`,
  )
  // If user cancels the dialog, abort
  if (keepOriginal === null) return
  // If user clicks OK, keep original (overwrite: false). If Cancel, overwrite (overwrite: true)
  const overwrite = !keepOriginal

  try {
    const response = await fetch(`http://localhost:8000/api/files/fix/${file.id}/apply`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        fixed_data: fixedData,
        overwrite,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to apply fix')
    }

    const result = await response.json()

    // Close the preview modal
    fixPreviewModal.value.show = false

    // Refresh the files list to update the structure_ok status
    await fetchFiles()
  } catch (error) {
    console.error('Apply fix failed:', error)
    alert(`❌ Failed to apply fix:\n\n${error instanceof Error ? error.message : String(error)}`)
  }
}

const closeFixPreview = () => {
  fixPreviewModal.value.show = false
  fixPreviewModal.value.file = null
  fixPreviewModal.value.original = null
  fixPreviewModal.value.fixed = null
  fixPreviewModal.value.loading = false
}

const downloadFile = (file: FileItem) => {
  // open the appropriate endpoint in a new tab (backend sets Content-Disposition)
  const url = getFileApiUrl(file, 'download')
  window.open(url, '_blank')
}

const downloadSelectedFiles = () => {
  selectedFiles.value.forEach((id) => {
    const file = files.value.find((f) => f.id === id)
    if (file) {
      downloadFile(file)
    }
  })
}

const deleteFile = (fileId: string) => {
  if (confirm('Are you sure you want to delete this file?')) {
    const file = files.value.find((f) => f.id === fileId)
    if (!file) return
    ;(async () => {
      try {
        const file = files.value.find((f) => f.id === fileId)
        if (!file) throw new Error('File not found')
        const url = getFileApiUrl(file, 'delete')
        const res = await fetch(url, { method: 'DELETE' })
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
          if (!file) throw new Error('File not found')
          const url = getFileApiUrl(file, 'delete')
          const res = await fetch(url, { method: 'DELETE' })
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

const useFile = (file: FileItem) => {
  router.push({ path: '/discussion', query: { file: file.path || file.name } })
}

// Move modal state and functions
const moveModal = ref({ show: false, dest: '' as string, targets: [] as string[] })

const openMoveModalForSelected = () => {
  moveModal.value.show = true
  moveModal.value.targets = [...selectedFiles.value]
  // default destination empty (root)
  moveModal.value.dest = ''
}

const closeMoveModal = () => {
  moveModal.value.show = false
  moveModal.value.targets = []
  moveModal.value.dest = ''
}

const moveFiles = async (targetsArg?: string[], destArg?: string) => {
  const targets = targetsArg ?? moveModal.value.targets
  const dest = destArg ?? moveModal.value.dest
  if (!targets.length) return closeMoveModal()
  try {
    // Map targets (which may be file ids) to file paths where possible
    const targetsToSend = targets.map((t) => {
      // if t looks like an id present in files, map to its path
      const f = files.value.find((fi) => fi.id === String(t))
      if (f && f.path) return f.path
      return t
    })

    const res = await fetch(`${API_BASE}/api/files/move`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ targets: targetsToSend, dest }),
    })
    const contentType = res.headers.get('content-type') || ''
    const text = await res.text()
    if (!res.ok) {
      // try to parse JSON error message
      try {
        const j = JSON.parse(text)
        throw new Error(j.detail || j.message || JSON.stringify(j))
      } catch (_) {
        throw new Error(text || `Move failed (${res.status})`)
      }
    }
    // parse response JSON
    let json: any = {}
    try {
      json = contentType.includes('application/json') ? JSON.parse(text) : {}
    } catch (_) {
      json = {}
    }
    if (json.errors && json.errors.length) {
      alert('Move completed with errors:\n' + JSON.stringify(json.errors, null, 2))
    }
    await fetchFiles()
    // remove moved from selection
    selectedFiles.value = selectedFiles.value.filter((id) => !targets.includes(id))
    closeMoveModal()
  } catch (err) {
    alert('Failed to move files: ' + String(err))
    console.error('Move error details:', err)
  }
}

// Drag & drop state and handlers
const draggingId = ref<string | null>(null)
const hoverFolder = ref<string | null>(null)

const onDragStart = (file: FileItem, e: DragEvent) => {
  draggingId.value = file.id
  // if the file is not selected, treat drag as single-file drag
  const targets = selectedFiles.value.includes(file.id) ? selectedFiles.value : [file.id]
  // store ids in dataTransfer so other windows/components can inspect if needed
  e.dataTransfer?.setData('application/json', JSON.stringify({ targets }))
  e.dataTransfer!.effectAllowed = 'move'
}

const onDragEnd = () => {
  draggingId.value = null
  hoverFolder.value = null
}

const onFolderDragEnter = (folderName: string) => {
  hoverFolder.value = folderName
}

const onFolderDragLeave = (folderName: string) => {
  if (hoverFolder.value === folderName) hoverFolder.value = null
}

const onDropOnFolder = async (folderName: string, e: DragEvent) => {
  e.preventDefault()
  const payloadText = e.dataTransfer?.getData('application/json')
  let targets: string[] = []
  if (payloadText) {
    try {
      const parsed = JSON.parse(payloadText)
      targets = parsed.targets || []
    } catch {}
  }
  // If no dataTransfer payload, fallback to selectedFiles or draggingId
  if (!targets.length) {
    targets = selectedFiles.value.length
      ? [...selectedFiles.value]
      : draggingId.value
        ? [draggingId.value]
        : []
  }
  if (!targets.length) return
  // call the move API with targets (ids) and dest folder
  await moveFiles(
    targets,
    currentFolder.value ? currentFolder.value + '/' + folderName : folderName,
  )
  draggingId.value = null
  hoverFolder.value = null
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

/* structure badge styles */
.structure-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  font-size: 12px;
  color: white;
  margin-right: 0.5rem;
}
.structure-badge.ok {
  background: #2ecc71;
}
.structure-badge.invalid {
  background: #e74c3c;
}
.structure-badge.unknown {
  background: #95a5a6;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* category badge shown for valid files: discussion (green) and draft (grey) */
.category-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  color: white;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
}
.category-badge.discussion {
  background: #2ecc71; /* green */
  color: #013220;
}
.category-badge.draft {
  background: #95a5a6; /* grey */
  color: #ffffff;
}
.category-badge.unknown {
  background: #95a5a6;
}

/* overlay badge for invalid files */
.structure-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 40;
}
.structure-banner {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(90deg, #ffb347, #ffcc33);
  color: #3b2f00;
  padding: 6px 10px;
  border-radius: 8px;
  font-weight: 600;
  box-shadow: 0 6px 18px rgba(255, 153, 51, 0.12);
}
.structure-banner svg {
  stroke: #3b2f00;
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

.file-card.dragging {
  opacity: 0.6;
  transform: scale(0.98);
}

.drop-target {
  border: 2px dashed rgba(52, 152, 219, 0.6);
  box-shadow: 0 6px 20px rgba(52, 152, 219, 0.08);
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
