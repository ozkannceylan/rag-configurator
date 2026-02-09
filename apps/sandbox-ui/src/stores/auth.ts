import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, TokenResponse, LoginRequest } from '@/types'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const accessToken = ref<string>(localStorage.getItem('access_token') || '')
  const refreshToken = ref<string>(localStorage.getItem('refresh_token') || '')
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value)

  // Actions
  async function login(credentials: LoginRequest) {
    loading.value = true
    error.value = null

    try {
      const response = await authApi.login(credentials)
      setTokens(response)
      return true
    } catch (err: any) {
      error.value = err.response?.data?.error?.message || 'Login failed'
      return false
    } finally {
      loading.value = false
    }
  }

  function setTokens(tokens: TokenResponse) {
    accessToken.value = tokens.access_token
    refreshToken.value = tokens.refresh_token
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      clearAuth()
    }
  }

  function clearAuth() {
    user.value = null
    accessToken.value = ''
    refreshToken.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  function initialize() {
    const token = localStorage.getItem('access_token')
    if (token) {
      accessToken.value = token
      refreshToken.value = localStorage.getItem('refresh_token') || ''
    }
  }

  return {
    user,
    accessToken,
    refreshToken,
    loading,
    error,
    isAuthenticated,
    login,
    logout,
    clearAuth,
    initialize,
  }
})
