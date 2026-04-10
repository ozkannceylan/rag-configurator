import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
    },
    {
      path: '/comparison',
      name: 'Comparison',
      component: () => import('@/views/ComparisonView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/evaluation',
      name: 'Evaluation',
      component: () => import('@/views/EvaluationView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  authStore.initialize()

  const isPublic = to.meta.public === true
  const requiresAuth = to.meta.requiresAuth === true || !isPublic

  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (isPublic && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
