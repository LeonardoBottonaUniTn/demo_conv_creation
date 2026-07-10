<template>
  <div class="settings-screen">
    <aside class="settings-nav">
      <div class="nav-header">
        <div class="nav-avatar">{{ userInitial }}</div>
        <div class="nav-user">
          <p class="nav-name">{{ displayName }}</p>
          <p class="nav-email">{{ displayEmail }}</p>
        </div>
      </div>
      <nav class="nav-links">
        <button
          v-for="item in navItems"
          :key="item.key"
          class="nav-link"
          :class="{ active: activeNav === item.key }"
          type="button"
          @click="activeNav = item.key"
        >
          {{ item.label }}
        </button>
      </nav>
    </aside>

    <section class="settings-content">
      <header class="page-header">
        <div>
          <p class="eyebrow">Settings / {{ activeItem.label }}</p>
          <h1>{{ activeItem.label }}</h1>
          <p class="subtitle">{{ activeItem.description }}</p>
        </div>
      </header>

      <div v-if="initialLoading" class="status-card">
        <span class="loader" />
        Loading your settings…
      </div>

      <template v-else>
        <ProfileTab
          v-if="activeNav === 'profile'"
          :user-initial="userInitial"
          :display-name="displayName"
          :profile-name="profileName"
          :profile-email="profileEmail"
          :profile-saving="profileSaving"
          :profile-message="profileMessage"
          @update:profileName="profileName = $event"
          @touched="flagProfileTouched"
          @reset="resetProfileForm"
          @save="saveProfile"
        />

        <ApiTab
          v-if="activeNav === 'api'"
          :provider="provider"
          :available-providers="availableProviders"
          :api-key="apiKey"
          :has-api-key="hasApiKey"
          :model="model"
          :available-models="availableModels"
          :quick-model-options="quickModelOptions"
          :loading="loading"
          :error="error"
          :success="success"
          :last-synced="lastSynced"
          @update:provider="onProviderChange"
          @update:apiKey="apiKey = $event"
          @update:model="model = $event"
          @reset="resetApiForm"
          @save="save"
        />

        <!--  <AppearanceTab
          v-if="activeNav === 'appearance'"
          :theme="appearanceTheme"
          :density="appearanceDensity"
          :accent="appearanceAccent"
          :accent-options="accentOptions"
          :accent-styles="accentStyles"
          :appearance-saving="appearanceSaving"
          :appearance-message="appearanceMessage"
          @update:theme="appearanceTheme = $event as AppearanceTheme"
          @update:density="appearanceDensity = $event as AppearanceDensity"
          @update:accent="appearanceAccent = $event as AccentKey"
          @reset="resetAppearance"
          @save="saveAppearance"
        />

        <NotificationsTab
          v-if="activeNav === 'notifications'"
          :product-updates="notificationProductUpdates"
          :security-alerts="notificationSecurityAlerts"
          :weekly-digest="notificationWeeklyDigest"
          :sms-alerts="notificationSmsAlerts"
          :notification-saving="notificationSaving"
          :notification-message="notificationMessage"
          @update:productUpdates="notificationProductUpdates = $event"
          @update:securityAlerts="notificationSecurityAlerts = $event"
          @update:weeklyDigest="notificationWeeklyDigest = $event"
          @update:smsAlerts="notificationSmsAlerts = $event"
          @reset="resetNotifications"
          @save="saveNotifications"
        /> -->

        <SecurityTab v-if="activeNav === 'security'" :security-state="securityState" />

        <AboutTab v-if="activeNav === 'about'" :last-synced="lastSynced" />
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useAuthFetch } from '../composables/useAuthFetch'
import { useAuthState } from '../composables/useAuthState'
import ProfileTab from './settings/ProfileTab.vue'
import ApiTab from './settings/ApiTab.vue'
import AppearanceTab from './settings/AppearanceTab.vue'
import NotificationsTab from './settings/NotificationsTab.vue'
import SecurityTab from './settings/SecurityTab.vue'
import AboutTab from './settings/AboutTab.vue'
import type { AccentKey, AccentOption, AccentStyles } from './settings/types'

type AppearanceTheme = 'system' | 'light' | 'dark'
type AppearanceDensity = 'cozy' | 'compact' | 'spacious'

const navItems = [
  {
    key: 'profile',
    label: 'Profile',
    description: 'Manage your personal details and public bio.',
  },
  {
    key: 'api',
    label: 'API Settings',
    description: 'Store your Groq or OpenAI API key and pick the default model.',
  },
  /*  {
    key: 'appearance',
    label: 'Appearance',
    description: 'Control theme, density, and accent colors.',
  },
  {
    key: 'notifications',
    label: 'Notifications',
    description: 'Choose which alerts reach your inbox or phone.',
  }, */
  {
    key: 'security',
    label: 'Security',
    description: 'Review sessions, MFA, and critical actions.',
  },
  {
    key: 'about',
    label: 'About',
    description: 'Workspace metadata and support channels.',
  },
] as const

type NavKey = (typeof navItems)[number]['key']

const { authState } = useAuthState()
const { authFetch } = useAuthFetch()

const API_BASE = import.meta.env.VITE_API_BASE || ''

type ProviderOption = {
  id: string
  label: string
}

const apiKey = ref('')
const hasApiKey = ref(false)
const provider = ref('groq')
const persistedProvider = ref('groq')
const model = ref('')
const availableModels = ref<string[]>([])
const availableProviders = ref<ProviderOption[]>([])
const modelsByProvider = ref<Record<string, string[]>>({})
const persistedModel = ref('')

const initialLoading = ref(true)
const loading = ref(false)
const error = ref('')
const success = ref('')
const lastSynced = ref('')

const activeNav = ref<NavKey>('profile')
const activeItem = computed(
  () => navItems.find((item) => item.key === activeNav.value) ?? navItems[0],
)

const profileName = ref('')
const profileEmail = ref('')
const profileMessage = ref('')
const profileSaving = ref(false)
const profileTouched = ref(false)
const profileSnapshot = ref({ name: '' })

const appearanceTheme = ref<AppearanceTheme>('system')
const appearanceDensity = ref<AppearanceDensity>('cozy')
const appearanceAccent = ref<AccentKey>('indigo')
const appearanceMessage = ref('')
const appearanceSaving = ref(false)
const appearanceSnapshot = ref({
  theme: appearanceTheme.value,
  density: appearanceDensity.value,
  accent: appearanceAccent.value,
})

const notificationProductUpdates = ref(true)
const notificationSecurityAlerts = ref(true)
const notificationWeeklyDigest = ref(false)
const notificationSmsAlerts = ref(false)
const notificationMessage = ref('')
const notificationSaving = ref(false)
const notificationSnapshot = ref({
  productUpdates: notificationProductUpdates.value,
  securityAlerts: notificationSecurityAlerts.value,
  weeklyDigest: notificationWeeklyDigest.value,
  smsAlerts: notificationSmsAlerts.value,
})

const securityState = ref({ devices: 3, passwordUpdated: 'Feb 3, 2026' })

const quickModelOptions = computed(() => Array.from(new Set(availableModels.value)).slice(0, 3))

const displayName = computed(() => profileName.value || 'LLM User')
const displayEmail = computed(() => profileEmail.value || 'user@example.com')
const userInitial = computed(() => displayName.value.charAt(0).toUpperCase() || 'U')

const accentOptions: AccentOption[] = [
  { key: 'indigo', label: 'Indigo' },
  { key: 'emerald', label: 'Emerald' },
  { key: 'amber', label: 'Amber' },
  { key: 'rose', label: 'Rose' },
]

const accentStyles: AccentStyles = {
  indigo: { background: '#eef2ff', color: '#312e81' },
  emerald: { background: '#ecfdf5', color: '#065f46' },
  amber: { background: '#fef3c7', color: '#92400e' },
  rose: { background: '#ffe4e6', color: '#9d174d' },
}

watch(
  () => authState.email,
  (email) => {
    const fallbackName = email ? email.split('@')[0] : 'LLM User'
    if (!profileSnapshot.value.name) {
      profileSnapshot.value = { name: fallbackName }
    }
    const nextName = profileSnapshot.value.name || fallbackName
    profileName.value = nextName
    profileEmail.value = email ?? 'user@example.com'
    profileTouched.value = false
  },
  { immediate: true },
)

watch(activeNav, (value) => {
  if (value !== 'api') {
    error.value = ''
    success.value = ''
  }
})

function flagProfileTouched() {
  profileTouched.value = true
}

function resetApiForm() {
  apiKey.value = ''
  provider.value = persistedProvider.value
  model.value = persistedModel.value
  availableModels.value = modelsByProvider.value[provider.value] || []
  error.value = ''
  success.value = ''
}

function onProviderChange(nextProvider: string) {
  provider.value = nextProvider
  availableModels.value = modelsByProvider.value[nextProvider] || []
  if (!availableModels.value.includes(model.value)) {
    model.value = availableModels.value[0] || ''
  }
}

function resetProfileForm() {
  profileName.value = profileSnapshot.value.name
  profileTouched.value = false
  profileMessage.value = ''
}

function resetAppearance() {
  appearanceTheme.value = appearanceSnapshot.value.theme
  appearanceDensity.value = appearanceSnapshot.value.density
  appearanceAccent.value = appearanceSnapshot.value.accent
  appearanceMessage.value = ''
}

function resetNotifications() {
  notificationProductUpdates.value = notificationSnapshot.value.productUpdates
  notificationSecurityAlerts.value = notificationSnapshot.value.securityAlerts
  notificationWeeklyDigest.value = notificationSnapshot.value.weeklyDigest
  notificationSmsAlerts.value = notificationSnapshot.value.smsAlerts
  notificationMessage.value = ''
}

const delay = (ms = 600) => new Promise((resolve) => setTimeout(resolve, ms))

async function saveProfile() {
  profileSaving.value = true
  profileMessage.value = ''
  await delay()
  profileSnapshot.value = { name: profileName.value }
  profileMessage.value = 'Profile updated successfully.'
  profileSaving.value = false
  profileTouched.value = false
}

async function saveAppearance() {
  appearanceSaving.value = true
  appearanceMessage.value = ''
  await delay()
  appearanceSnapshot.value = {
    theme: appearanceTheme.value,
    density: appearanceDensity.value,
    accent: appearanceAccent.value,
  }
  appearanceMessage.value = 'Theme preferences saved.'
  appearanceSaving.value = false
}

async function saveNotifications() {
  notificationSaving.value = true
  notificationMessage.value = ''
  await delay()
  notificationSnapshot.value = {
    productUpdates: notificationProductUpdates.value,
    securityAlerts: notificationSecurityAlerts.value,
    weeklyDigest: notificationWeeklyDigest.value,
    smsAlerts: notificationSmsAlerts.value,
  }
  notificationMessage.value = 'Notification settings updated.'
  notificationSaving.value = false
}

function formatTimestamp(date: Date = new Date()) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

async function fetchSettings() {
  initialLoading.value = true
  error.value = ''
  success.value = ''
  try {
    const res = await authFetch(`${API_BASE}/api/settings`)
    if (!res.ok) {
      let detail = 'Failed to load settings'
      try {
        const data = await res.json()
        detail = data.detail || detail
      } catch (e) {
        // ignore parse errors
      }
      throw new Error(detail)
    }
    const data = (await res.json()) as {
      provider: string
      model: string
      hasApiKey: boolean
      availableModels: string[]
      availableProviders: ProviderOption[]
      modelsByProvider: Record<string, string[]>
    }
    provider.value = data.provider
    persistedProvider.value = data.provider
    model.value = data.model
    persistedModel.value = data.model
    hasApiKey.value = data.hasApiKey
    availableModels.value = data.availableModels || []
    availableProviders.value = data.availableProviders || []
    modelsByProvider.value = data.modelsByProvider || {}
    lastSynced.value = formatTimestamp()
  } catch (e: any) {
    error.value = e?.message || 'Failed to load settings'
  } finally {
    initialLoading.value = false
  }
}

async function save() {
  if (!authState.token) return
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    const body: Record<string, unknown> = {
      provider: provider.value,
      model: model.value,
    }
    if (apiKey.value !== '') {
      body.apiKey = apiKey.value
    }

    const res = await authFetch(`${API_BASE}/api/settings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      let detail = 'Failed to save settings'
      try {
        const data = await res.json()
        detail = data.detail || detail
      } catch (e) {
        // ignore parse errors
      }
      throw new Error(detail)
    }
    const data = (await res.json()) as {
      provider: string
      model: string
      hasApiKey: boolean
      availableModels: string[]
    }
    provider.value = data.provider
    persistedProvider.value = data.provider
    model.value = data.model
    persistedModel.value = data.model
    hasApiKey.value = data.hasApiKey
    availableModels.value = data.availableModels || []
    apiKey.value = ''
    lastSynced.value = formatTimestamp()
    success.value = 'Settings saved successfully.'
  } catch (e: any) {
    error.value = e?.message || 'Failed to save settings'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSettings()
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&display=swap');

.settings-screen {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 250px 1fr;
  background: transparent;
  color: #0f172a;
  font-family: 'Space Grotesk', 'Segoe UI', sans-serif;
}

.settings-nav {
  background: #0b1222;
  color: #f8fafc;
  padding: 2.5rem 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.nav-header {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.nav-avatar {
  width: 32px;
  height: 32px;
  border-radius: 14px;
  background: linear-gradient(135deg, #3b82f6, #9333ea);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.35rem;
  font-weight: 600;
}

.nav-name {
  margin: 0;
  font-weight: 600;
  font-size: 1rem;
}

.nav-email {
  margin: 0.15rem 0 0;
  font-size: 0.75rem;
  color: rgba(248, 250, 252, 0.7);
}

.nav-links {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.nav-link {
  background: transparent;
  border: none;
  color: rgba(248, 250, 252, 0.7);
  padding: 0.6rem 0.75rem;
  text-align: left;
  border-radius: 10px;
  font-size: 0.95rem;
  transition: 0.2s ease;
}

.nav-link.active,
.nav-link:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

.settings-content {
  padding: 2.5rem 3rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header h1 {
  margin: 0.25rem 0;
  font-size: 2rem;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.75rem;
  margin: 0;
  color: #818cf8;
}

.subtitle {
  margin: 0;
  color: #6c7288;
  max-width: 640px;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: #fff;
  padding: 1.25rem 1.5rem;
  border-radius: 16px;
  box-shadow: 0 15px 45px rgba(15, 23, 42, 0.08);
  font-weight: 500;
}

.loader {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3b82f6;
  animation: spin 0.9s linear infinite;
}

.panel {
  background: #fff;
  border-radius: 18px;
  padding: 1.75rem;
  box-shadow: 0 20px 55px rgba(15, 23, 42, 0.08);
}

.profile-panel {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
}

.avatar-large {
  width: 104px;
  height: 104px;
  border-radius: 24px;
  background: linear-gradient(135deg, #020617, #0f172a);
  color: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  font-weight: 600;
}

.profile-form {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.profile-head {
  margin-bottom: 0.75rem;
}

.muted {
  margin: 0.15rem 0;
  color: #6c7288;
}

.muted.small {
  font-size: 0.85rem;
}

.field-label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  margin: 1rem 0 0.35rem;
  color: #1e293b;
}

input,
select,
textarea {
  width: 100%;
  border-radius: 12px;
  border: 1px solid #d9ddea;
  padding: 0.75rem 0.9rem;
  font-size: 0.95rem;
  transition:
    border 0.15s ease,
    box-shadow 0.15s ease;
  background: #f9fafc;
}

textarea {
  resize: none;
}

input:focus,
select:focus,
textarea:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
  outline: none;
}

.helper {
  margin: 0.35rem 0 0;
  font-size: 0.8rem;
  color: #6c7288;
}

.actions-bar {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.btn {
  border: none;
  border-radius: 12px;
  padding: 0.75rem 1.4rem;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn.primary {
  background: #0f172a;
  color: #ffffff;
  box-shadow: 0 12px 25px rgba(15, 23, 42, 0.25);
}

.btn.ghost {
  background: transparent;
  color: #475569;
  border: 1px solid rgba(148, 163, 184, 0.4);
}

.btn.danger {
  background: #ef4444;
  color: #fff;
  box-shadow: 0 10px 25px rgba(239, 68, 68, 0.35);
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.inline-error {
  margin: 0.35rem 0 0;
  color: #dc2626;
  font-size: 0.8rem;
}

.inline-success {
  margin: 0.35rem 0 0;
  color: #15803d;
  font-size: 0.85rem;
}

.alert-stack {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.alert {
  padding: 0.85rem 1rem;
  border-radius: 12px;
  font-size: 0.9rem;
  margin: 0;
}

.alert.error {
  background: #fee2e2;
  color: #b91c1c;
}

.alert.success {
  background: #dcfce7;
  color: #15803d;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin: 1rem 0 0.5rem;
}

.chip {
  border-radius: 999px;
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.chip.safe {
  background: #ecfdf5;
  color: #047857;
}

.chip.neutral {
  background: #f1f5f9;
  color: #0f172a;
}

.model-chips {
  margin-top: 0.75rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.chip-button {
  border: none;
  background: rgba(99, 102, 241, 0.12);
  color: #4338ca;
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.chip-button:hover {
  background: rgba(99, 102, 241, 0.2);
}

.status-panel {
  margin-top: 1.5rem;
  border: 1px dashed #d8dbe8;
  border-radius: 16px;
  padding: 1.25rem;
}

.status-panel ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  color: #475569;
}

.badge {
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.badge.success {
  background: #dcfce7;
  color: #166534;
}

.badge.warning {
  background: #fee2e2;
  color: #b91c1c;
}

.badge.neutral {
  background: #e2e8f0;
  color: #0f172a;
}

.appearance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.accent-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin: 1rem 0;
}

.accent-chip {
  border: none;
  border-radius: 999px;
  padding: 0.4rem 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}

.accent-chip.active {
  box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.1);
  transform: translateY(-2px);
}

.toggle-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.toggle-item {
  display: flex;
  gap: 1rem;
  align-items: center;
  padding: 0.9rem 1rem;
  border-radius: 14px;
  border: 1px solid #e4e7f2;
}

.toggle-item input {
  position: absolute;
  opacity: 0;
}

.toggle-control {
  width: 42px;
  height: 24px;
  border-radius: 999px;
  background: #cbd5f5;
  position: relative;
  flex-shrink: 0;
}

.toggle-control::after {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  top: 3px;
  left: 3px;
  transition: transform 0.2s ease;
}

.toggle-item input:checked + .toggle-control {
  background: #4f46e5;
}

.toggle-item input:checked + .toggle-control::after {
  transform: translateX(18px);
}

.toggle-item strong {
  display: block;
  font-size: 0.95rem;
  margin-bottom: 0.15rem;
}

.toggle-item p {
  margin: 0;
  color: #6c7288;
  font-size: 0.85rem;
}

.status-grid {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  color: #475569;
}

.danger-panel {
  margin-top: 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #fee6e6;
  background: #fff5f5;
  border-radius: 18px;
  padding: 1.25rem;
}

.danger-panel .eyebrow {
  color: #ef4444;
}

.about-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.about-grid article {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 1rem;
  background: #fafbff;
}

.stack > * + * {
  margin-top: 1rem;
}

@media (max-width: 1100px) {
  .settings-screen {
    grid-template-columns: 1fr;
  }

  .settings-nav {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    padding: 1.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  }

  .nav-links {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .settings-content {
    padding: 1.5rem;
  }

  .profile-panel {
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .settings-nav {
    flex-direction: column;
    align-items: flex-start;
  }

  .actions-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .btn {
    width: 100%;
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
