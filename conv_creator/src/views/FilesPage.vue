<template>
  <div class="files-page">
    <!-- Navigation Header -->
    <div class="nav-header">
      <router-link to="/" class="back-button"> ← Back to Home </router-link>
      <h1 class="page-title">Files Management</h1>
      <div class="nav-spacer"></div>
    </div>

    <div class="container">
      <div class="page-description">
        <p>Upload and manage your discussion files</p>
      </div>

      <section class="upload-section">
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
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".json,.pkl,.csv"
              @change="handleFileSelect"
              class="file-input"
            />
            <button class="upload-button" @click="triggerFileSelect">Choose Files</button>
          </div>
        </div>
      </section>

      <!-- Files List -->
      <section class="files-section">
        <div class="section-header">
          <h2>Available Files</h2>
          <div class="file-stats">
            <span>{{ files.length }} files</span>
            <span>{{ formatBytes(totalSize) }}</span>
          </div>
        </div>

        <div class="files-grid" v-if="files.length > 0">
          <div
            v-for="file in files"
            :key="file.id"
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
              <button class="action-button delete" @click.stop="deleteFile(file.id)" title="Delete">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M3 6h18" />
                  <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                  <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14,2 14,8 20,8" />
          </svg>
          <h3>No files uploaded yet</h3>
          <p>Upload your first discussion file to get started</p>
        </div>
      </section>

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

// Load existing files from backend directory
onMounted(async () => {
  try {
    // Load the existing files from the backend directory
    const existingFiles = [
      { name: 'bp_130_0.json', type: 'json', path: '/src/backend/bp_130_0.json' },
      { name: 'bp_130_0_d3.json', type: 'json', path: '/src/backend/bp_130_0_d3.json' },
      { name: 'bp_130_users.json', type: 'json', path: '/src/backend/bp_130_users.json' },
      { name: 'V2_Should_all_drugs_be_legalised.pkl', type: 'pkl', path: null },
    ]

    // Load files with their actual content
    for (const file of existingFiles) {
      try {
        let content = null
        let fileSize = 0

        if (file.type === 'json' && file.path) {
          // Try to import JSON files directly using static imports
          try {
            if (file.name === 'bp_130_0.json') {
              const module = await import('../backend/bp_130_0.json')
              content = module.default
            } else if (file.name === 'bp_130_0_d3.json') {
              const module = await import('../backend/bp_130_0_d3.json')
              content = module.default
            } else if (file.name === 'bp_130_users.json') {
              const module = await import('../backend/bp_130_users.json')
              content = module.default
            }

            if (content) {
              fileSize = JSON.stringify(content).length
            }
          } catch (importError) {
            content = `Could not load JSON file. This might be because the file is not properly configured for import in Vite.`
            console.warn(`Import failed for ${file.name}:`, importError)
          }
        } else if (file.type === 'pkl') {
          // For pkl files, we can't load them directly in the browser
          content =
            'PKL files cannot be previewed in the browser. This is a Python pickle file that needs to be processed on the server.'
          fileSize = 0
        }

        files.value.push({
          id: Math.random().toString(36).substr(2, 9),
          name: file.name,
          type: file.type,
          size: fileSize,
          uploadDate: new Date(Date.now() - Math.floor(Math.random() * 10000000000)),
          content: content,
        })
      } catch (fileError) {
        console.error(`Error loading file ${file.name}:`, fileError)
        // Add file without content if loading fails
        files.value.push({
          id: Math.random().toString(36).substr(2, 9),
          name: file.name,
          type: file.type,
          size: 0,
          uploadDate: new Date(Date.now() - Math.floor(Math.random() * 10000000000)),
          content: `Error loading file: ${fileError instanceof Error ? fileError.message : 'Unknown error'}`,
        })
      }
    }
  } catch (error) {
    console.error('Error loading existing files:', error)
  }
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

const handleFiles = (fileList: File[]) => {
  fileList.forEach((file) => {
    const fileItem: FileItem = {
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      type: file.name.split('.').pop()?.toLowerCase() || 'unknown',
      size: file.size,
      uploadDate: new Date(),
    }

    // Read file content
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        if (fileItem.type === 'json') {
          fileItem.content = JSON.parse(e.target?.result as string)
        } else {
          fileItem.content = e.target?.result
        }
      } catch (error) {
        console.error('Error reading file:', error)
      }
    }
    reader.readAsText(file)

    files.value.push(fileItem)
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
  let content = 'Content not available'

  if (file.content) {
    if (file.type === 'json') {
      // Pretty print JSON content
      content =
        typeof file.content === 'string' ? file.content : JSON.stringify(file.content, null, 2)
    } else if (file.type === 'pkl') {
      // For pkl files, show the placeholder message
      content = file.content
    } else {
      // For other file types, convert to string
      content =
        typeof file.content === 'string' ? file.content : JSON.stringify(file.content, null, 2)
    }
  } else {
    content =
      'File content could not be loaded. This might be because the file was not properly imported or there was an error reading it.'
  }

  previewModal.value = {
    show: true,
    file,
    content,
  }
}

const closePreview = () => {
  previewModal.value.show = false
}

const downloadFile = (file: FileItem) => {
  // Create download link
  const content = file.content ? JSON.stringify(file.content, null, 2) : ''
  const blob = new Blob([content], { type: 'application/octet-stream' })
  const url = URL.createObjectURL(blob)

  const a = document.createElement('a')
  a.href = url
  a.download = file.name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const deleteFile = (fileId: string) => {
  if (confirm('Are you sure you want to delete this file?')) {
    files.value = files.value.filter((f) => f.id !== fileId)
    selectedFiles.value = selectedFiles.value.filter((id) => id !== fileId)
  }
}

const deleteSelectedFiles = () => {
  if (confirm(`Are you sure you want to delete ${selectedFiles.value.length} file(s)?`)) {
    files.value = files.value.filter((f) => !selectedFiles.value.includes(f.id))
    selectedFiles.value = []
  }
}

const useSelectedFiles = () => {
  // Navigate to discussion page with selected files
  router.push('/discussion')
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
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
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
