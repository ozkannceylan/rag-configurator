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
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  authStore.initialize()

  if (!to.meta.public && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.public && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
