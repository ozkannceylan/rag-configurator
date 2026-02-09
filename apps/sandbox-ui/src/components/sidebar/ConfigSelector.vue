<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useConfigStore } from '@/stores/config'
import type { RAGConfigSummary } from '@/types'

const configStore = useConfigStore()

const isDisabledStatus = (status?: string) => {
  return status === 'processing' || status === 'running' || status === 'failed' || status === 'error'
}

const displayStatus = (status?: string) => {
  if (!status) return 'ready'
  if (status === 'completed') return 'ready'
  if (status === 'running') return 'processing'
  return status
}

const statusColor = (status?: string) => {
  const s = displayStatus(status)
  if (s === 'ready') return 'bg-green-100 text-green-800'
  if (s === 'processing') return 'bg-yellow-100 text-yellow-800'
  if (s === 'failed' || s === 'error') return 'bg-red-100 text-red-800'
  return 'bg-gray-100 text-gray-800'
}

const selectedValue = computed({
  get: () => configStore.selectedConfig?.id || '',
  set: (value: string) => {
    if (value) {
      void configStore.selectConfigById(value)
    } else {
      configStore.selectConfig(null)
    }
  },
})

const handleRefresh = async () => {
  await configStore.fetchConfigs()
}

const getRetrievalMethodLabel = (method: string) => {
  const labels: Record<string, string> = {
    naive: 'Vector Only',
    keyword: 'Keyword',
    hybrid: 'Hybrid',
    graph: 'Graph',
    hybrid_graph: 'Hybrid + Graph',
  }
  return labels[method] || method
}

onMounted(() => {
  configStore.fetchConfigs()
})
</script>

<template>
  <div class="config-selector">
    <!-- Config dropdown + refresh -->
    <div class="flex items-center gap-2">
      <select
        v-model="selectedValue"
        class="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        :disabled="configStore.loading"
      >
        <option value="" disabled>
          {{ configStore.loading ? 'Loading...' : 'Select a RAG configuration' }}
        </option>
        <option
          v-for="config in configStore.configs"
          :key="config.id"
          :value="config.id"
          :disabled="isDisabledStatus(config.status)"
        >
          {{ config.name }} ({{ displayStatus(config.status) }})
        </option>
      </select>
      <button
        @click="handleRefresh"
        :disabled="configStore.loading"
        class="p-2 text-gray-500 hover:text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
        title="Refresh configs"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
        </svg>
      </button>
    </div>

    <!-- Error display -->
    <div v-if="configStore.error" class="mt-2 text-xs text-red-600 bg-red-50 px-3 py-2 rounded">
      {{ configStore.error }}
    </div>

    <!-- No configs warning -->
    <div v-if="!configStore.loading && !configStore.hasConfigs && !configStore.error" class="mt-2 text-xs text-gray-500">
      No configurations available. Create one in the configurator.
    </div>

    <!-- Selected config details -->
    <div v-if="configStore.selectedConfig" class="mt-3 bg-gray-50 border border-gray-200 rounded-lg p-3">
      <div class="flex items-center gap-2 mb-2">
        <span
          class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
          :class="statusColor(configStore.selectedConfig?.status)"
        >
          {{ displayStatus(configStore.selectedConfig?.status) }}
        </span>
        <span class="text-sm font-semibold text-gray-900">{{ configStore.selectedConfig.name }}</span>
      </div>

      <div v-if="configStore.selectedConfig.description" class="text-xs text-gray-500 mb-2">
        {{ configStore.selectedConfig.description }}
      </div>

      <div class="space-y-1 text-xs">
        <div class="flex">
          <span class="text-gray-400 w-20">Agent:</span>
          <span class="text-gray-700">{{ configStore.selectedConfig?.agent?.template || 'unknown' }}</span>
        </div>
        <div class="flex">
          <span class="text-gray-400 w-20">Retrieval:</span>
          <span class="text-gray-700">{{ getRetrievalMethodLabel(configStore.selectedConfig?.retrieval?.method || 'unknown') }}</span>
        </div>
        <div class="flex">
          <span class="text-gray-400 w-20">LLM:</span>
          <span class="text-gray-700">
            {{ configStore.selectedConfig?.models?.llm?.provider || 'unknown' }} /
            {{ configStore.selectedConfig?.models?.llm?.model_name || 'unknown' }}
          </span>
        </div>
        <div class="flex">
          <span class="text-gray-400 w-20">Embedding:</span>
          <span class="text-gray-700">
            {{ configStore.selectedConfig?.models?.embedding?.provider || 'unknown' }} /
            {{ configStore.selectedConfig?.models?.embedding?.model_name || 'unknown' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.config-selector {
  padding: 16px;
  border-bottom: 1px solid #e0e0e0;
}
</style>
