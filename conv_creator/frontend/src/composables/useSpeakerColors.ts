// Use a fixed palette of 10 visually distinct colors. For each palette entry
// we provide: color (accent), background (light variant), onAccent (text color
// to use on the accent color), onBackground (text color to use on the light
// background).
// Internal palette of 10 distinct colors.
const PALETTE = [
  { color: '#1E88E5', background: '#E3F2FD', onAccent: '#ffffff', onBackground: '#0b2540' }, // blue
  { color: '#43A047', background: '#E8F5E9', onAccent: '#ffffff', onBackground: '#062a10' }, // green
  { color: '#F4511E', background: '#FBE9E7', onAccent: '#ffffff', onBackground: '#3a1208' }, // red-orange
  //{ color: '#8E24AA', background: '#F3E5F5', onAccent: '#ffffff', onBackground: '#2b0a2e' }, // purple
  { color: '#FB8C00', background: '#FFF3E0', onAccent: '#ffffff', onBackground: '#3a2300' }, // orange
  //{ color: '#E53935', background: '#FFEBEE', onAccent: '#ffffff', onBackground: '#2f0a0a' }, // red
  //{ color: '#00897B', background: '#E0F2F1', onAccent: '#ffffff', onBackground: '#042b27' }, // teal
  //{ color: '#FFB300', background: '#FFF8E1', onAccent: '#ffffff', onBackground: '#3c2a00' }, // amber (black text on accent)
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

  // Palette exhausted: generate a new unique color and append to palette.
  // This guarantees uniqueness at runtime by extending the palette.
  const newIdx = PALETTE.length
  const gen = generateAdditionalColor(newIdx)
  PALETTE.push(gen)
  assignments.set(n, newIdx)
  usedIndices.add(newIdx)
  return gen
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
    // if exhausted, generate and assign a new unique color
    const newIdx = PALETTE.length
    const gen = generateAdditionalColor(newIdx)
    PALETTE.push(gen)
    assignments.set(n, newIdx)
    usedIndices.add(newIdx)
    result[n] = newIdx
  })
  return result
}

// Generate an accent/background/onAccent/onBackground object for a new
// palette entry. We use the item index to pick a hue spread using the
// golden angle to avoid clustering. Returns same object shape as PALETTE
function generateAdditionalColor(index: number) {
  const goldenAngle = 137.50776405003785
  const hue = (index * goldenAngle) % 360
  const accent = hslToHex(hue, 65, 45) // saturated mid-light accent
  const background = hslToHex(hue, 80, 96) // very light background
  const onAccent = readableTextColor(accent)
  const onBackground = '#0b0b0b'
  return { color: accent, background, onAccent, onBackground }
}

// Convert HSL to hex color string. h in [0,360), s and l in [0,100]
function hslToHex(h: number, s: number, l: number) {
  s /= 100
  l /= 100
  const k = (n: number) => (n + h / 30) % 12
  const a = s * Math.min(l, 1 - l)
  const f = (n: number) => {
    const val = l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)))
    return Math.round(255 * val)
      .toString(16)
      .padStart(2, '0')
  }
  return `#${f(0)}${f(8)}${f(4)}`
}

// Choose readable text color (black or white) for a given hex color
function readableTextColor(hex: string) {
  const rgb = hexToRgb(hex)
  if (!rgb) return '#000000'
  // relative luminance
  const [r, g, b] = [rgb.r, rgb.g, rgb.b].map((v) => {
    const c = v / 255
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
  })
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
  // contrast against white (lum=1) and black (lum=0)
  const contrastWhite = 1.05 / (lum + 0.05)
  const contrastBlack = (lum + 0.05) / 0.05
  return contrastWhite >= contrastBlack ? '#ffffff' : '#000000'
}

function hexToRgb(hex: string) {
  const m = hex.replace('#', '')
  if (m.length !== 6) return null
  return {
    r: parseInt(m.substring(0, 2), 16),
    g: parseInt(m.substring(2, 4), 16),
    b: parseInt(m.substring(4, 6), 16),
  }
}

export default function useSpeakerColors() {
  return { getSpeakerColors }
}
