// Types for chat components

export interface ChatMessage {
  id: number
  text: string
  sender: string
  addressees: string[] // Array of addressee names
  timestamp: Date
}

export interface User {
  name: string
  description: string
}
