export function decodeTokenExpiry(token: string): number | null {
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')))
    return typeof payload.exp === 'number' ? payload.exp : null
  } catch {
    return null
  }
}

export function isTokenExpired(token: string | null, leewaySeconds = 30): boolean {
  if (!token) return true
  const exp = decodeTokenExpiry(token)
  if (!exp) return true
  return Date.now() / 1000 >= exp - leewaySeconds
}
