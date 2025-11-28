import { ref, reactive } from 'vue'
import type { User } from '../types/chat'

const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

export function useUsers() {
  const personas = ref<User[]>([])

  const availablePersonas = ref<User[]>([])
  const currentPersona = ref<User | null>(null)

  const loadUsers = async (file: string) => {
    try {
      // preserve folder separators when sending a file path to the backend
      let res = await fetch(`${API_BASE}/api/users/${encodeURI(file)}`)
      // If the backend expects just the basename, retry using it when 404
      if (!res.ok && res.status === 404) {
        const base = file.split('/').pop() || file
        if (base !== file) {
          res = await fetch(`${API_BASE}/api/users/${encodeURI(base)}`)
        }
      }
      if (!res.ok) throw new Error('Failed to load users')
      console.log('Fetching users from backend')
      const data = await res.json()
      const users = Array.isArray(data.users) ? data.users : data
      personas.value = users.map((user: any) => ({
        name: user.speaker,
        description: user.description,
      }))

      //TODO: test why is called so many times
      //console.log('Loaded personas from backend:', personas.value)

      availablePersonas.value = personas.value.map((persona, index) => ({
        id: index + 2,
        name: persona.name,
        description: persona.description,
      }))

      currentPersona.value = availablePersonas.value[0] || null
    } catch (err) {
      console.error('Failed to load personas from backend:', err)
    }
  }

  const switchPersona = (personaName: string) => {
    const persona = availablePersonas.value.find((p) => p.name === personaName)
    if (persona) {
      currentPersona.value = persona
    }
  }

  return {
    personas,
    availablePersonas,
    currentPersona,
    loadUsers,
    switchPersona,
  }
}
