<template>
  <header class="workspace-header">
    <div class="header-inner">
      <div class="cluster-left">
        <router-link to="/" class="back-chip">
          <span class="icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" role="presentation" focusable="false">
              <path
                d="M14.5 5l-7 7 7 7"
                fill="none"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </span>
          <span>Back home</span>
        </router-link>

        <div class="workspace-stack">
          <div class="workspace-chip" aria-hidden="true">{{ workspaceInitials }}</div>
          <div class="workspace-info">
            <span class="workspace-label">Workspace</span>
            <div class="workspace-name-row">
              <span class="workspace-name">{{ workspaceName }}</span>
            </div>
          </div>
        </div>

        <nav class="section-links">
          <router-link to="/files" class="section-link">Files</router-link>
          <router-link to="/discussion" class="section-link">Discussion</router-link>
          <router-link to="/annotate" class="section-link">Label</router-link>
        </nav>
      </div>

      <div class="cluster-right">
        <template v-if="authState.token">
          <button
            class="avatar-button"
            type="button"
            @click="toggleMenu"
            aria-haspopup="true"
            :aria-expanded="menuOpen ? 'true' : 'false'"
          >
            <div class="avatar" aria-hidden="true">{{ avatarInitial }}</div>
          </button>
          <div v-if="menuOpen" class="profile-menu">
            <div class="profile-header">
              <div class="avatar small" aria-hidden="true">{{ avatarInitial }}</div>
              <div class="profile-text">
                <div class="label">Signed in</div>
                <div class="email">{{ authState.email }}</div>
              </div>
            </div>
            <button class="menu-item" type="button" @click="goToSettings">Settings</button>
            <button class="menu-item" type="button" @click="logout">Logout</button>
          </div>
        </template>
        <router-link v-else to="/login" class="btn btn-primary btn-sm">Sign in</router-link>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthState } from '../composables/useAuthState'

const router = useRouter()
const { authState, clearAuth } = useAuthState()

const workspaceName = 'LLMberjack'
const workspaceInitials = workspaceName.slice(0, 2).toUpperCase()

const menuOpen = ref(false)

const avatarInitial = computed(() => {
  const email = authState.email || ''
  const first = email.trim().charAt(0)
  return first ? first.toUpperCase() : 'U'
})

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function goToSettings() {
  menuOpen.value = false
  router.push({ name: 'settings' })
}

function logout() {
  clearAuth()
  menuOpen.value = false
  router.push({ name: 'login' })
}
</script>

<style scoped>
.workspace-header {
  position: sticky;
  top: 0;
  z-index: 120;
  padding: 0.85rem 2rem;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 0.65rem 1.5rem;
  border-radius: 20px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.cluster-left {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.back-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.4rem 1rem;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #f8fafc;
  color: #0f172a;
  font-weight: 600;
  text-decoration: none;
  transition:
    transform 0.15s ease,
    box-shadow 0.2s ease;
}

.back-chip .icon {
  width: 1.4rem;
  height: 1.4rem;
  display: inline-flex;
}

.back-chip svg {
  width: 100%;
  height: 100%;
}

.back-chip:hover {
  transform: translateX(-2px);
  box-shadow: 0 12px 18px rgba(15, 23, 42, 0.12);
}

.workspace-stack {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 0.75rem;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  background: #ffffff;
}

.workspace-chip {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(135deg, #111f79, #4b7bec);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  letter-spacing: 0.05em;
  box-shadow: 0 12px 24px rgba(72, 99, 221, 0.35);
}

.workspace-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.workspace-label {
  font-size: 0.7rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #64748b;
}

.workspace-name-row {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.workspace-name {
  font-weight: 700;
  color: #0f172a;
  font-size: 1.2rem;
}

.workspace-pill {
  padding: 0.1rem 0.55rem;
  border-radius: 999px;
  background: rgba(249, 115, 22, 0.12);
  color: #b45309;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.section-links {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.2rem;
  border-radius: 999px;
  background: #f1f5f9;
}

.section-link {
  text-decoration: none;
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 600;
  color: #475569;
  transition:
    background 0.2s ease,
    color 0.2s ease;
}

.section-link.router-link-active,
.section-link:hover {
  background: #0f172a;
  color: #ffffff;
}

.cluster-right {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  position: relative;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  background: #ecfdf5;
  color: #047857;
  font-weight: 600;
  font-size: 0.85rem;
}

.status-pill .dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.25);
}

.btn-sm {
  padding: 0.35rem 0.9rem;
  font-size: 0.85rem;
  border-radius: 999px;
}

.avatar-button {
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

.avatar {
  width: 38px;
  height: 38px;
  border-radius: 14px;
  background: linear-gradient(135deg, #0f172a, #1e293b);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  font-weight: 600;
  box-shadow: 0 12px 18px rgba(15, 23, 42, 0.25);
}

.avatar.small {
  width: 30px;
  height: 30px;
  font-size: 0.8rem;
}

.profile-menu {
  position: absolute;
  top: 110%;
  right: 0;
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.18);
  min-width: 230px;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  z-index: 140;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  margin-bottom: 0.3rem;
}

.profile-text .label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #94a3b8;
}

.profile-text .email {
  font-size: 0.88rem;
  color: #0f172a;
  word-break: break-all;
}

.menu-item {
  border: none;
  background: transparent;
  text-align: left;
  padding: 0.4rem 0.35rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  color: #0f172a;
  border-radius: 10px;
}

.menu-item:hover {
  background: #f5f7ff;
}

@media (max-width: 768px) {
  .header-inner {
    flex-direction: column;
    align-items: stretch;
  }

  .cluster-left,
  .cluster-right {
    justify-content: space-between;
  }

  .section-links {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
