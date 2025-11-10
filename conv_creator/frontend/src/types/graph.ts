// Types for the discussion graph

export interface ArgumentNode {
  id: string
  speaker: string
  text: string
}

export interface ChatMessage {
  text: string
  type: 'user' | 'bot'
  nodeId: string
}

// Unified payload used when requesting "add to chat" from different sources
export interface AddToChatPayload {
  text: string
  nodeId?: string
  node?: ArgumentNode
  source?: 'chat' | 'graph'
}

export interface Position {
  x: number
  y: number
}

export interface NodePosition {
  position: 'absolute'
  left: string
  top: string
  transform?: string
}

export type ViewMode = 'tree' | 'single'

export type BranchesData = ArgumentNode[][]
