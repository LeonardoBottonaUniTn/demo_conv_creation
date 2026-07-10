import { reactive, readonly } from 'vue'

interface AuthState {
  token: string | null
  email: string | null
  refreshToken: string | null
}

const REFRESH_TOKEN_KEY = 'auth_refresh_token'

const state = reactive<AuthState>({
  token: localStorage.getItem('auth_token'),
  email: localStorage.getItem('auth_email'),
  refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY),
})

let refreshInFlight: Promise<boolean> | null = null

export function useAuthState() {
  function setAuth(token: string, email: string, refreshToken?: string | null) {
    state.token = token
    state.email = email
    localStorage.setItem('auth_token', token)
    localStorage.setItem('auth_email', email)
    if (refreshToken) {
      state.refreshToken = refreshToken
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
    }
  }

  function clearAuth() {
    state.token = null
    state.email = null
    state.refreshToken = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_email')
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }

  async function refreshAccessToken(): Promise<boolean> {
    if (refreshInFlight) return refreshInFlight

    const refreshToken = state.refreshToken || localStorage.getItem(REFRESH_TOKEN_KEY)
    if (!refreshToken) return false

    refreshInFlight = (async () => {
      try {
        const API_BASE = import.meta.env.VITE_API_BASE || ''
        const res = await fetch(`${API_BASE}/api/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })
        if (!res.ok) return false

        const data = (await res.json()) as {
          access_token: string
          refresh_token?: string
          user?: { email?: string }
        }
        setAuth(
          data.access_token,
          data.user?.email || state.email || '',
          data.refresh_token || refreshToken,
        )
        return true
      } catch {
        return false
      } finally {
        refreshInFlight = null
      }
    })()

    return refreshInFlight
  }

  return {
    authState: readonly(state),
    setAuth,
    clearAuth,
    refreshAccessToken,
  }
}
