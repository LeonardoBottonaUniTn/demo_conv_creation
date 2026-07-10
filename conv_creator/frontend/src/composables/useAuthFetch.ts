import { isTokenExpired } from './authToken'
import { useAuthState } from './useAuthState'

async function redirectToLogin(redirectPath?: string) {
  const { default: router } = await import('../router')
  if (router.currentRoute.value.name === 'login') return
  await router.push({
    name: 'login',
    query: redirectPath ? { redirect: redirectPath } : undefined,
  })
}

export function useAuthFetch() {
  const { authState, refreshAccessToken, clearAuth } = useAuthState()

  function authHeaders(extra?: HeadersInit): HeadersInit {
    const headers: Record<string, string> = {}
    if (authState.token) {
      headers.Authorization = `Bearer ${authState.token}`
    }
    if (!extra) {
      return headers
    }
    if (extra instanceof Headers) {
      extra.forEach((value, key) => {
        headers[key] = value
      })
      return headers
    }
    if (Array.isArray(extra)) {
      extra.forEach(([key, value]) => {
        if (value !== undefined) {
          headers[key] = value
        }
      })
      return headers
    }
    return { ...headers, ...extra }
  }

  async function authFetch(input: RequestInfo | URL, init?: RequestInit) {
    const doFetch = () =>
      fetch(input, {
        ...init,
        headers: authHeaders(init?.headers),
      })

    let res = await doFetch()

    if (res.status === 401) {
      const refreshed = await refreshAccessToken()
      if (refreshed) {
        res = await doFetch()
      }
      if (res.status === 401) {
        clearAuth()
        const redirectPath =
          typeof window !== 'undefined'
            ? `${window.location.pathname}${window.location.search}`
            : undefined
        await redirectToLogin(redirectPath)
      }
    }

    return res
  }

  return { authFetch, authHeaders, isTokenExpired }
}
