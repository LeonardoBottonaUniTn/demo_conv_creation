<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal-panel">
      <header class="modal-header">
        <h2>Select a discussion file</h2>
        <button class="close" @click="close">✕</button>
      </header>

      <div class="modal-body">
        <div v-if="loading" class="loading">Loading files...</div>
        <div v-else-if="error" class="error">{{ error }}</div>

        <div v-else class="files-list">
          <input v-model="query" placeholder="Filter files..." class="filter" />
          <div v-if="filtered.length === 0" class="empty">No files found</div>
          <ul>
            <li
              v-for="f in filtered"
              :key="f.id"
              :class="{ selected: selectedId === f.id }"
              @click="select(f)"
            >
              <div class="name">{{ f.name }}</div>
              <div class="meta">{{ f.type.toUpperCase() }} • {{ formatBytes(f.size) }}</div>
            </li>
          </ul>
        </div>
      </div>

      <footer class="modal-footer">
        <button class="secondary" @click="close">Cancel</button>
        <button class="primary" :disabled="!selectedId" @click="confirm">Open Discussion</button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface FileItem {
  id: string
  name: string
  type: string
  size: number
}

const emit = defineEmits<{
  (e: 'select', fileName: string): void
  (e: 'close'): void
}>()

const selectedId = ref<string | null>(null)
const files = ref<FileItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const query = ref('')

const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://127.0.0.1:8000'

const fetchFiles = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await fetch(`${API_BASE}/api/files`)
    if (!res.ok) throw new Error(`Failed to list files (${res.status})`)
    const list = await res.json()
    files.value = list.map((f: any) => {
      const rawPath = f.path || f.name
      // normalize legacy stored paths that may include a leading 'files_root/' prefix
      const normalized = String(rawPath).replace(/^files_root[\\/]/, '')
      return {
        id: String(f.id ?? Math.random().toString(36).substr(2, 9)),
        name: f.name,
        path: normalized,
        type: f.type,
        size: f.size,
      }
    })
  } catch (err: any) {
    console.error('Error loading files for selector:', err?.message ?? err)
    error.value = err?.message ?? String(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchFiles()
})

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return files.value
  return files.value.filter(
    (f) => f.name.toLowerCase().includes(q) || f.type.toLowerCase().includes(q),
  )
})

const select = (f: FileItem) => {
  selectedId.value = f.id
}

const confirm = () => {
  const f = files.value.find((x) => x.id === selectedId.value)
  if (f) emit('select', (f as any).path || f.name)
}

const close = () => {
  emit('close')
}

const formatBytes = (bytes: number) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}
.modal-panel {
  width: min(900px, 95%);
  max-height: 85vh;
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.modal-header {
  padding: 14px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #eee;
}
.modal-body {
  padding: 12px 16px;
  overflow: auto;
  flex: 1;
}
.files-list ul {
  list-style: none;
  padding: 0;
  margin: 8px 0 0 0;
}
.files-list li {
  padding: 10px 12px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}
.files-list li.selected {
  background: #f1f7ff;
  border-color: #cfe3ff;
}
.modal-footer {
  padding: 10px 16px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid #eee;
}
.primary {
  background: #2563eb;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
}
.secondary {
  background: transparent;
  border: 1px solid #ddd;
  padding: 8px 12px;
  border-radius: 6px;
}
.filter {
  width: 100%;
  padding: 8px 10px;
  margin-bottom: 8px;
  border: 1px solid #e6e6e6;
  border-radius: 6px;
}
.close {
  background: transparent;
  border: none;
  font-size: 18px;
  cursor: pointer;
}
.name {
  font-weight: 600;
}
.meta {
  font-size: 12px;
  color: #666;
}
</style>
