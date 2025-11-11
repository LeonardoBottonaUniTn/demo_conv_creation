// Use a fixed palette of 10 visually distinct colors. For each palette entry
// we provide: color (accent), background (light variant), onAccent (text color
// to use on the accent color), onBackground (text color to use on the light
// background).
// Internal palette of 10 distinct colors.
const PALETTE = [
  { color: '#1E88E5', background: '#E3F2FD', onAccent: '#ffffff', onBackground: '#0b2540' }, // blue
  { color: '#43A047', background: '#E8F5E9', onAccent: '#ffffff', onBackground: '#062a10' }, // green
  { color: '#F4511E', background: '#FBE9E7', onAccent: '#ffffff', onBackground: '#3a1208' }, // red-orange
  { color: '#8E24AA', background: '#F3E5F5', onAccent: '#ffffff', onBackground: '#2b0a2e' }, // purple
  { color: '#FB8C00', background: '#FFF3E0', onAccent: '#ffffff', onBackground: '#3a2300' }, // orange
  { color: '#E53935', background: '#FFEBEE', onAccent: '#ffffff', onBackground: '#2f0a0a' }, // red
  { color: '#00897B', background: '#E0F2F1', onAccent: '#ffffff', onBackground: '#042b27' }, // teal
  { color: '#FFB300', background: '#FFF8E1', onAccent: '#ffffff', onBackground: '#3c2a00' }, // amber (black text on accent)
]

// Maintain a runtime mapping to ensure uniqueness of assignments while the
// app is running. We assign a palette index to each seen speaker name. If
// the palette is exhausted, we will fall back to hashed assignments (and
// log a warning) because it's impossible to guarantee uniqueness beyond
// palette length.
const assignments = new Map<string, number>()
const usedIndices = new Set<number>()

function simpleHash(str: string) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    // eslint-disable-next-line no-bitwise
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
    // eslint-disable-next-line no-bitwise
    hash = hash & hash
  }
  return Math.abs(hash)
}

export function getSpeakerColors(name: string | null | undefined) {
  const n = (name || 'unknown').toString()

  // Return existing assignment if present
  if (assignments.has(n)) {
    return PALETTE[assignments.get(n) as number]
  }

  // Preferred index based on hash
  const preferred = simpleHash(n) % PALETTE.length

  // If preferred is free, use it; otherwise find nearest free slot
  if (!usedIndices.has(preferred)) {
    assignments.set(n, preferred)
    usedIndices.add(preferred)
    return PALETTE[preferred]
  }

  // Linear probe for a free index
  for (let i = 1; i < PALETTE.length; i++) {
    const idx = (preferred + i) % PALETTE.length
    if (!usedIndices.has(idx)) {
      assignments.set(n, idx)
      usedIndices.add(idx)
      return PALETTE[idx]
    }
  }

  // Palette exhausted: fall back to deterministic hashed index (may collide).
  const fallbackIdx = preferred
  console.warn('[useSpeakerColors] palette exhausted — assigning non-unique color for', n)
  assignments.set(n, fallbackIdx)
  return PALETTE[fallbackIdx]
}

// Utility to reset assignments (useful for tests or when loading a known set)
export function resetSpeakerAssignments() {
  assignments.clear()
  usedIndices.clear()
}

// Deterministically assign palette entries for a given list of names. This
// clears existing assignments and assigns in sorted order so results are
// reproducible across loads. Returns a map of name->paletteIndex.
export function assignPaletteForList(names: string[]) {
  resetSpeakerAssignments()
  const sorted = Array.from(new Set(names.map((n) => (n || 'unknown').toString()))).sort()
  const result: Record<string, number> = {}
  sorted.forEach((n) => {
    const preferred = simpleHash(n) % PALETTE.length
    if (!usedIndices.has(preferred)) {
      assignments.set(n, preferred)
      usedIndices.add(preferred)
      result[n] = preferred
      return
    }
    for (let i = 1; i < PALETTE.length; i++) {
      const idx = (preferred + i) % PALETTE.length
      if (!usedIndices.has(idx)) {
        assignments.set(n, idx)
        usedIndices.add(idx)
        result[n] = idx
        return
      }
    }
    // if exhausted, assign preferred (may collide)
    assignments.set(n, preferred)
    result[n] = preferred
  })
  return result
}

export default function useSpeakerColors() {
  return { getSpeakerColors }
}
