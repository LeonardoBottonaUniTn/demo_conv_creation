import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import DiscussionPage from '../views/DiscussionPage.vue'
import FilesPage from '../views/FilesPage.vue'
import LoginPage from '../views/LoginPage.vue'
import SettingsPage from '../views/SettingsPage.vue'
import AnnotationPage from '../views/AnnotationPage.vue'
import { isTokenExpired } from '../composables/authToken'
import { useAuthState } from '../composables/useAuthState'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomePage,
      meta: {
        title: 'Discussion Creator - Home',
        requiresAuth: true,
      },
    },
    {
      path: '/login',
      name: 'login',
      component: LoginPage,
      meta: {
        title: 'Discussion Creator - Login',
      },
    },
    {
      // Accept an optional dynamic `file` param so routes like
      // /discussion or /discussion/:file both match. We still support
      // the query style (?file=...) because the page will read params
      // first and fall back to query string.
      path: '/discussion/:file?',
      name: 'discussion',
      component: DiscussionPage,
      meta: {
        title: 'Discussion Creator - Discussion Interface',
        requiresAuth: true,
      },
    },
    {
      path: '/files',
      name: 'files',
      component: FilesPage,
      meta: {
        title: 'Discussion Creator - Files Management',
        requiresAuth: true,
      },
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsPage,
      meta: {
        title: 'Discussion Creator - Settings',
        requiresAuth: true,
      },
    },
    {
      path: '/annotate/:file?',
      name: 'annotate',
      component: AnnotationPage,
      meta: {
        title: 'Discussion Creator - Annotate Conversation',
        requiresAuth: true,
      },
    },
    // Catch-all route for 404 pages
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

// Add navigation guards for dynamic page titles and simple auth
router.beforeEach(async (to, from, next) => {
  if (to.meta?.title) {
    document.title = to.meta.title as string
  }

  const requiresAuth = Boolean(to.meta && (to.meta as any).requiresAuth)
  const token = localStorage.getItem('auth_token')
  const { refreshAccessToken, clearAuth } = useAuthState()

  if (requiresAuth) {
    if (!token) {
      return next({ name: 'login', query: { redirect: to.fullPath } })
    }
    if (isTokenExpired(token)) {
      const refreshed = await refreshAccessToken()
      if (!refreshed) {
        clearAuth()
        return next({ name: 'login', query: { redirect: to.fullPath } })
      }
    }
  }

  if (to.name === 'login' && token && !isTokenExpired(token)) {
    // If already logged in, avoid showing login page again
    return next((from && from.name) ? from : { name: 'home' })
  }
  next()
})

export default router
