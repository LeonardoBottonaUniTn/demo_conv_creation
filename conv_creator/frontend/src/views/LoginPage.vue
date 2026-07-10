<template>
  <div class="login-page">
    <div class="login-card card">
      <h1 class="login-title">Sign in</h1>
      <p class="login-subtitle">Access LLMberjack with your account</p>

      <form class="login-form" @submit.prevent="onSubmit">
        <div class="field">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="email"
            type="email"
            autocomplete="email"
            required
            :disabled="loading"
          />
        </div>

        <div class="field">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            minlength="8"
            required
            :disabled="loading"
          />
        </div>

        <p v-if="error" class="error-text">{{ error }}</p>

        <button class="btn btn-primary full-width" type="submit" :disabled="loading">
          <span v-if="!loading">Sign in</span>
          <span v-else>Signing in...</span>
        </button>
      </form>

      <p class="login-help">
        New here?
        <button class="link-button" type="button" @click="registerAccount" :disabled="loading">
          Create account
        </button>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthState } from '../composables/useAuthState'

const router = useRouter()
const route = useRoute()
const { setAuth } = useAuthState()

const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const API_BASE = import.meta.env.VITE_API_BASE || ''

async function callAuth(path: string, body: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    let detail = 'Request failed'
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch (e) {
      // ignore parse errors
    }
    throw new Error(detail)
  }
  return (await res.json()) as {
    access_token: string
    refresh_token?: string
    user: { email: string }
  }
}

function redirectAfterLogin() {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
  if (redirect && redirect !== '/login') {
    router.push(redirect)
    return
  }
  router.push({ name: 'home' })
}

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    const data = await callAuth('/api/auth/login', {
      email: email.value,
      password: password.value,
    })
    setAuth(data.access_token, data.user.email, data.refresh_token)
    redirectAfterLogin()
  } catch (e: any) {
    error.value = e?.message || 'Login failed'
  } finally {
    loading.value = false
  }
}

async function registerAccount() {
  error.value = ''
  loading.value = true
  try {
    const data = await callAuth('/api/auth/register', {
      email: email.value,
      password: password.value,
    })
    setAuth(data.access_token, data.user.email, data.refresh_token)
    redirectAfterLogin()
  } catch (e: any) {
    error.value = e?.message || 'Registration failed'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.login-card {
  width: 100%;
  max-width: 420px;
}

.login-title {
  margin: 0 0 0.25rem 0;
  color: var(--text-900);
}

.login-subtitle {
  margin: 0 0 1.25rem 0;
  color: var(--text-700);
  font-size: 0.95rem;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.field label {
  font-size: 0.9rem;
  color: var(--text-900);
}

.field input {
  border-radius: 8px;
  border: 1px solid #dcdfe4;
  padding: 0.55rem 0.75rem;
  font-size: 0.95rem;
}

.field input:focus {
  outline: 2px solid rgba(52, 152, 219, 0.4);
  outline-offset: 1px;
}

.error-text {
  color: var(--danger);
  font-size: 0.85rem;
  margin: 0.25rem 0 0.5rem 0;
}

.full-width {
  width: 100%;
  margin-top: 0.25rem;
}

.login-help {
  margin-top: 0.9rem;
  font-size: 0.85rem;
  color: var(--text-700);
}

.link-button {
  border: none;
  background: none;
  padding: 0;
  margin: 0;
  color: var(--primary);
  cursor: pointer;
  text-decoration: underline;
}

.link-button:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
