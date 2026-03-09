import { reactive, readonly } from 'vue'

interface AuthState {
  token: string | null
  email: string | null
}

const state = reactive<AuthState>({
  token: localStorage.getItem('auth_token'),
  email: localStorage.getItem('auth_email'),
})

export function useAuthState() {
  function setAuth(token: string, email: string) {
    state.token = token
    state.email = email
    localStorage.setItem('auth_token', token)
    localStorage.setItem('auth_email', email)
  }

  function clearAuth() {
    state.token = null
    state.email = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('auth_email')
  }

  return {
    authState: readonly(state),
    setAuth,
    clearAuth,
  }
}
