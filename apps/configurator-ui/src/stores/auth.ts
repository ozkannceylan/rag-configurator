import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User, TokenResponse } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value)

  // Actions
  async function login(email: string, password: string) {
    loading.value = true
    error.value = null
    
    try {
      const response: TokenResponse = await authApi.login(email, password)
      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token
      
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)
      
      // Load user info
      await loadUser()
      
      return true
    } catch (err: any) {
      if (err.code === 'ERR_NETWORK' || err.message === 'Network Error') {
        error.value = 'Sunucuya bağlanılamıyor. Gateway ve Config Service çalıştığından emin olun.'
      } else if (err.response?.data?.error?.message) {
        error.value = err.response.data.error.message
      } else if (err.response?.data?.message) {
        error.value = err.response.data.message
      } else {
        error.value = err.message || 'Giriş başarısız'
      }
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(name: string, email: string, password: string) {
    loading.value = true
    error.value = null
    
    try {
      const response: TokenResponse = await authApi.register({ name, email, password })
      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token
      
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)
      
      await loadUser()
      
      return true
    } catch (err: any) {
      if (err.code === 'ERR_NETWORK' || err.message === 'Network Error') {
        error.value = 'Sunucuya bağlanılamıyor. Gateway ve Config Service çalıştığından emin olun.'
      } else if (err.response?.data?.error?.message) {
        error.value = err.response.data.error.message
      } else if (err.response?.data?.message) {
        error.value = err.response.data.message
      } else {
        error.value = err.message || 'Kayıt başarısız'
      }
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch (err) {
      // Ignore errors on logout
    } finally {
      clearAuth()
    }
  }

  function clearAuth() {
    user.value = null
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  function clearError() {
    error.value = null
  }

  async function loadUser() {
    if (!accessToken.value) return
    
    try {
      user.value = await authApi.getMe()
    } catch (err: any) {
      // If /me endpoint doesn't exist (404), don't clear auth
      if (err.response?.status !== 404) {
        clearAuth()
      }
    }
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) return false
    
    try {
      const response = await authApi.refresh(refreshToken.value)
      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token
      
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)
      
      return true
    } catch (err) {
      clearAuth()
      return false
    }
  }

  function loadFromStorage() {
    const storedAccess = localStorage.getItem('access_token')
    const storedRefresh = localStorage.getItem('refresh_token')
    
    if (storedAccess && storedRefresh) {
      accessToken.value = storedAccess
      refreshToken.value = storedRefresh
      loadUser()
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
    register,
    logout,
    clearAuth,
    clearError,
    loadUser,
    refreshAccessToken,
    loadFromStorage,
  }
})
