import { ref, reactive } from 'vue'
import type { ChatUser, UserPersona } from '../types/chat'

const API_BASE = (import.meta.env.VITE_API_BASE as string) || 'http://localhost:8000'

export function useUsers() {
  const personas = ref<UserPersona[]>([])

  const currentUser = reactive<ChatUser>({
    id: 1,
    name: 'Leonardo',
    isOnline: true,
  })

  const availablePersonas = ref<ChatUser[]>([])
  const currentPersona = ref<ChatUser | null>(null)

  const loadUsers = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/users`)
      if (!res.ok) throw new Error('Failed to load users')
      const data = await res.json()
      personas.value = data.map((user: any) => ({
        name: user.speaker,
        description: user.argumentative_style,
        stance: user.stance,
        stance_summary: user.stance_summary,
        subunits: user.subunits,
      }))

      availablePersonas.value = personas.value.map((persona, index) => ({
        id: index + 2,
        name: persona.name,
        description: persona.description,
        stance: persona.stance as 'positive' | 'negative',
        isOnline: true,
        lastSeen: new Date(),
      }))

      currentPersona.value = availablePersonas.value[0] || null
    } catch (err) {
      console.error('Failed to load personas from backend:', err)
    }
  }

  const switchPersona = (personaId: number) => {
    const persona = availablePersonas.value.find((p) => p.id === personaId)
    if (persona) {
      currentPersona.value = persona
    }
  }

  const getPersonaResponses = (stance: 'positive' | 'negative') => {
    const positiveResponses = [
      'I believe we can absolutely turn this around with the right innovations!',
      'Technology and collective action are our strongest tools here.',
      'The data shows promising pathways for positive change.',
      "We're seeing remarkable progress in renewable energy solutions.",
      'Community organizing has already made significant impacts.',
      'Every action we take collectively builds momentum for change.',
    ]

    const negativeResponses = [
      'The structural barriers make this extremely challenging.',
      "Current market realities don't support rapid transformation.",
      'Historical evidence shows systemic resistance to change.',
      'The economic framework fundamentally conflicts with environmental needs.',
      "We're dealing with deeply entrenched institutional problems.",
      'The scale of change needed exceeds current system capabilities.',
    ]

    return stance === 'positive' ? positiveResponses : negativeResponses
  }

  const getRandomPersona = (): ChatUser => {
    const randomIndex = Math.floor(Math.random() * availablePersonas.value.length)
    return availablePersonas.value[randomIndex]
  }

  const getThesisStatement = (): string => {
    return "Can we reverse climate change? This is one of the most critical questions of our time. While some argue that technological innovation and collective action can lead us to a sustainable future, others believe that systemic barriers and economic realities make this goal nearly impossible to achieve. What's your perspective on humanity's ability to reverse climate change?"
  }

  return {
    personas,
    currentUser,
    availablePersonas,
    currentPersona,
    loadUsers,
    switchPersona,
    getPersonaResponses,
    getRandomPersona,
    getThesisStatement,
  }
}
