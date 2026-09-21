import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { RAGConfig, RAGConfigSummary } from '@/types'
import { configApi } from '@/api/configs'
import { apiErrorMessage } from '@/api/errors'

export const useConfigStore = defineStore('config', () => {
  // State
  const configs = ref<RAGConfigSummary[]>([])
  const selectedConfig = ref<RAGConfig | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const hasConfigs = computed(() => configs.value.length > 0)
  const readyConfigs = computed(() =>
    configs.value.filter(
      (c) => c.status === 'ready' || c.status === 'completed' || c.status === undefined
    )
  )

  // Actions
  async function fetchConfigs() {
    loading.value = true
    error.value = null

    try {
      const response = await configApi.list(1, 100)
      configs.value = response.items
      
      // Restore last selected config from localStorage
      const lastConfigId = localStorage.getItem('last_selected_config')
      if (lastConfigId) {
        await selectConfigById(lastConfigId)
      }
    } catch (err) {
      error.value = apiErrorMessage(err) ?? 'Failed to load configs'
    } finally {
      loading.value = false
    }
  }

  function selectConfig(config: RAGConfig | null) {
    selectedConfig.value = config
    if (config?.id) {
      localStorage.setItem('last_selected_config', config.id)
    } else {
      localStorage.removeItem('last_selected_config')
    }
  }

  async function selectConfigById(id: string) {
    const summary = configs.value.find(c => c.id === id)
    if (!summary) {
      selectConfig(null)
      return
    }

    try {
      const fullConfig = await configApi.get(id)
      selectConfig(fullConfig)
    } catch {
      // Fallback to summary when full config fails to load
      selectConfig(summary as unknown as RAGConfig)
    }
  }

  return {
    configs,
    selectedConfig,
    loading,
    error,
    hasConfigs,
    readyConfigs,
    fetchConfigs,
    selectConfig,
    selectConfigById,
  }
})
