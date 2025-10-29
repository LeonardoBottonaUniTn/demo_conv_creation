import { ref, reactive } from 'vue'
import type { User } from '../types/chat'

const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

export function useUsers() {
  const personas = ref<User[]>([])

  const availablePersonas = ref<User[]>([])
  const currentPersona = ref<User | null>(null)

  const loadUsers = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/users`)
      if (!res.ok) throw new Error('Failed to load users')
      const data = await res.json()
      const users = Array.isArray(data.users) ? data.users : data
      personas.value = users.map((user: any) => ({
        name: user.speaker,
        description: user.description,
      }))

      console.log('Loaded personas from bblblblbackend:', personas.value)

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

  const getThesisStatement = (): string => {
    return "Can we reverse climate change? This is one of the most critical questions of our time. While some argue that technological innovation and collective action can lead us to a sustainable future, others believe that systemic barriers and economic realities make this goal nearly impossible to achieve. What's your perspective on humanity's ability to reverse climate change?"
  }

  return {
    personas,
    availablePersonas,
    currentPersona,
    loadUsers,
    switchPersona,
    getThesisStatement,
  }
}
