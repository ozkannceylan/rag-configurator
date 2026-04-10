import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/wizard',
      name: 'wizard-new',
      component: () => import('@/views/WizardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/wizard/:id',
      name: 'wizard-edit',
      component: () => import('@/views/WizardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/config/:id',
      name: 'config-detail',
      component: () => import('@/views/ConfigDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/templates',
      name: 'templates',
      component: () => import('@/views/TemplatesView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  // Load auth from storage on first navigation
  if (!authStore.accessToken && localStorage.getItem('access_token')) {
    authStore.loadFromStorage()
  }
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (to.name === 'login' && authStore.isAuthenticated) {
    next({ name: 'dashboard' })
  } else {
    next()
  }
})

export default router
