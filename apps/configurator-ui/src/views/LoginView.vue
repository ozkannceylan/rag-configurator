<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          RAG Configurator
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          {{ isLogin ? 'Sign in to your account' : 'Create a new account' }}
        </p>
      </div>

      <div class="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
        <!-- Toggle -->
        <div class="flex justify-center mb-6">
          <div class="flex rounded-md shadow-sm">
            <button
              @click="isLogin = true"
              :class="[
                isLogin ? 'bg-primary-600 text-white' : 'bg-white text-gray-700',
                'px-4 py-2 text-sm font-medium rounded-l-md border border-gray-300'
              ]"
            >
              Login
            </button>
            <button
              @click="isLogin = false"
              :class="[
                !isLogin ? 'bg-primary-600 text-white' : 'bg-white text-gray-700',
                'px-4 py-2 text-sm font-medium rounded-r-md border border-gray-300 border-l-0'
              ]"
            >
              Register
            </button>
          </div>
        </div>

        <!-- Login Form -->
        <form v-if="isLogin" @submit.prevent="handleLogin" class="space-y-6">
          <div>
            <label for="email" class="block text-sm font-medium text-gray-700">Email</label>
            <input
              id="email"
              v-model="loginForm.email"
              type="email"
              required
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          <div>
            <label for="password" class="block text-sm font-medium text-gray-700">Password</label>
            <input
              id="password"
              v-model="loginForm.password"
              type="password"
              required
              minlength="8"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          <div v-if="authStore.error" class="text-red-600 text-sm">
            {{ authStore.error }}
          </div>

          <button
            type="submit"
            :disabled="authStore.loading"
            class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
          >
            {{ authStore.loading ? 'Signing in...' : 'Sign in' }}
          </button>
        </form>

        <!-- Register Form -->
        <form v-else @submit.prevent="handleRegister" class="space-y-6">
          <div>
            <label for="name" class="block text-sm font-medium text-gray-700">Name</label>
            <input
              id="name"
              v-model="registerForm.name"
              type="text"
              required
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          <div>
            <label for="reg-email" class="block text-sm font-medium text-gray-700">Email</label>
            <input
              id="reg-email"
              v-model="registerForm.email"
              type="email"
              required
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          <div>
            <label for="reg-password" class="block text-sm font-medium text-gray-700">Password</label>
            <input
              id="reg-password"
              v-model="registerForm.password"
              type="password"
              required
              minlength="8"
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          <div>
            <label for="confirm-password" class="block text-sm font-medium text-gray-700">Confirm Password</label>
            <input
              id="confirm-password"
              v-model="registerForm.confirmPassword"
              type="password"
              required
              class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          <div v-if="passwordMismatch" class="text-red-600 text-sm">
            Passwords do not match
          </div>

          <div v-if="authStore.error" class="text-red-600 text-sm">
            {{ authStore.error }}
          </div>

          <button
            type="submit"
            :disabled="authStore.loading || passwordMismatch"
            class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
          >
            {{ authStore.loading ? 'Creating account...' : 'Create account' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const isLogin = ref(true)

const loginForm = ref({
  email: '',
  password: '',
})

const registerForm = ref({
  name: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const passwordMismatch = computed(() => {
  return registerForm.value.password !== registerForm.value.confirmPassword &&
    registerForm.value.confirmPassword.length > 0
})

async function handleLogin() {
  const success = await authStore.login(loginForm.value.email, loginForm.value.password)
  
  if (success) {
    const redirect = route.query.redirect as string
    router.push(redirect || '/')
  }
}

async function handleRegister() {
  if (passwordMismatch.value) return
  
  const success = await authStore.register(
    registerForm.value.name,
    registerForm.value.email,
    registerForm.value.password
  )
  
  if (success) {
    router.push('/')
  }
}
</script>
