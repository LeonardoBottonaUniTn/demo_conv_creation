import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import DiscussionPage from '../views/DiscussionPage.vue'
import FilesPage from '../views/FilesPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomePage,
      meta: {
        title: 'Discussion Creator - Home',
      },
    },
    {
      path: '/discussion',
      name: 'discussion',
      component: DiscussionPage,
      meta: {
        title: 'Discussion Creator - Discussion Interface',
      },
    },
    {
      path: '/files',
      name: 'files',
      component: FilesPage,
      meta: {
        title: 'Discussion Creator - Files Management',
      },
    },
    // Catch-all route for 404 pages
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

// Add navigation guards for dynamic page titles
router.beforeEach((to, from, next) => {
  if (to.meta?.title) {
    document.title = to.meta.title as string
  }
  next()
})

export default router
