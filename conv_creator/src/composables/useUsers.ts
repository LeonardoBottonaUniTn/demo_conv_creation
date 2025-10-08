import { ref, reactive } from 'vue'
import type { ChatUser, UserPersona, RawUserData } from '../types/chat'
import usersData from '../backend/bp_130_users.json'

export function useUsers() {
  const personas = ref<UserPersona[]>(
    (usersData as RawUserData[]).map((user) => ({
      name: user.speaker,
      description: user.argumentative_style,
      stance: user.stance as 'positive' | 'negative',
      stance_summary: user.stance_summary,
      subunits: user.subunits,
    })),
  )

  const currentUser = reactive<ChatUser>({
    id: 1,
    name: 'Leonardo',
    isOnline: true,
  })

  const availablePersonas = ref<ChatUser[]>(
    personas.value.map((persona, index) => ({
      id: index + 2,
      name: persona.name,
      description: persona.description,
      stance: persona.stance,
      isOnline: true,
      lastSeen: new Date(),
    })),
  )

  const currentPersona = ref<ChatUser>(availablePersonas.value[0])

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
    switchPersona,
    getPersonaResponses,
    getRandomPersona,
    getThesisStatement,
  }
}
