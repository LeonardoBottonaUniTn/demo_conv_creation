// Types for chat components

export interface ChatMessage {
  id: number
  referenceId?: string
  text: string
  speaker: string
  addressees: string[] // Array of addresseee names
}

export interface User {
  name: string
  description: string
}
