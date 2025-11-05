// Types for the discussion graph

export interface ArgumentNode {
  id: string
  text: string
}

export interface ChatMessage {
  text: string
  type: 'user' | 'bot'
  nodeId: string
  nodeType: string
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
