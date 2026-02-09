import { defineStore } from 'pinia'
import { ref } from 'vue'
import { configApi } from '@/api/configs'
import type { RAGConfig, PaginatedResponse } from '@/types'

export const useConfigStore = defineStore('config', () => {
  // State
  const configs = ref<RAGConfig[]>([])
  const currentConfig = ref<RAGConfig | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const total = ref(0)

  // Actions
  async function fetchConfigs(page = 1, pageSize = 20) {
    loading.value = true
    error.value = null
    
    try {
      const response: PaginatedResponse<RAGConfig> = await configApi.list(page, pageSize)
      configs.value = response.items
      total.value = response.total
      return response
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Failed to fetch configs'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchConfig(id: string) {
    loading.value = true
    error.value = null
    
    try {
      const config = await configApi.get(id)
      currentConfig.value = config
      return config
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Failed to fetch config'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createConfig(data: Partial<RAGConfig>) {
    loading.value = true
    error.value = null
    
    try {
      const config = await configApi.create(data)
      configs.value.unshift(config)
      return config
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Failed to create config'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateConfig(id: string, data: Partial<RAGConfig>) {
    loading.value = true
    error.value = null
    
    try {
      const config = await configApi.update(id, data)
      const index = configs.value.findIndex(c => c.id === id)
      if (index !== -1) {
        configs.value[index] = config
      }
      if (currentConfig.value?.id === id) {
        currentConfig.value = config
      }
      return config
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Failed to update config'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteConfig(id: string) {
    loading.value = true
    error.value = null
    
    try {
      await configApi.delete(id)
      configs.value = configs.value.filter(c => c.id !== id)
      if (currentConfig.value?.id === id) {
        currentConfig.value = null
      }
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Failed to delete config'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function duplicateConfig(id: string) {
    loading.value = true
    error.value = null
    
    try {
      const config = await configApi.duplicate(id)
      configs.value.unshift(config)
      return config
    } catch (err: any) {
      error.value = err.response?.data?.message || 'Failed to duplicate config'
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    configs,
    currentConfig,
    loading,
    error,
    total,
    fetchConfigs,
    fetchConfig,
    createConfig,
    updateConfig,
    deleteConfig,
    duplicateConfig,
    clearError,
  }
})
