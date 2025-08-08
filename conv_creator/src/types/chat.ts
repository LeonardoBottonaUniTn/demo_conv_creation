// Types for chat components

export interface ChatMessage {
  id: number
  text: string
  sender: number
  timestamp: Date
}

export interface ChatUser {
  id: number
  name: string
  isOnline: boolean
  lastSeen?: Date
  description?: string
  stance?: 'positive' | 'negative'
}

export interface UserPersona {
  name: string
  description: string
  stance: 'positive' | 'negative'
}
