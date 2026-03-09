export type AccentKey = 'indigo' | 'emerald' | 'amber' | 'rose'

export interface AccentOption {
  key: AccentKey
  label: string
}

export type AccentStyles = Record<AccentKey, { background: string; color: string }>
