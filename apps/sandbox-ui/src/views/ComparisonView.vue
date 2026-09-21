<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-4">
        <router-link to="/" class="text-gray-500 hover:text-gray-700">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </router-link>
        <h1 class="text-xl font-bold text-gray-900">Config Comparison</h1>
      </div>
      <button
        @click="handleLogout"
        class="px-3 py-1.5 text-sm text-red-600 hover:text-red-700"
      >
        Logout
      </button>
    </header>

    <!-- Query Input -->
    <div class="bg-white border-b border-gray-200 px-6 py-4">
      <div class="max-w-4xl mx-auto flex gap-3">
        <input
          v-model="query"
          type="text"
          placeholder="Enter your query to compare both configs..."
          class="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          @keydown.enter="submitQuery"
          :disabled="isLoading"
        />
        <button
          @click="submitQuery"
          :disabled="!canSubmit"
          class="px-6 py-2.5 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ isLoading ? 'Comparing...' : 'Compare' }}
        </button>
      </div>
    </div>

    <!-- Config Selectors + Results -->
    <div class="flex-1 overflow-auto">
      <div class="grid grid-cols-2 gap-0 h-full">
        <!-- Left Panel -->
        <div class="border-r border-gray-200 flex flex-col">
          <div class="bg-white border-b border-gray-200 px-4 py-3">
            <label class="block text-xs font-medium text-gray-500 mb-1">Config A</label>
            <select
              v-model="configIdA"
              class="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              :disabled="isLoading"
            >
              <option value="" disabled>Select a configuration</option>
              <option
                v-for="config in readyConfigs"
                :key="config.id"
                :value="config.id"
              >
                {{ config.name }}
              </option>
            </select>
          </div>
          <div class="flex-1 overflow-y-auto p-4">
            <ComparisonResult
              v-if="resultA"
              :result="resultA"
              label="A"
            />
            <div v-else-if="isLoading && configIdA" class="flex items-center justify-center h-32">
              <div class="text-sm text-gray-500">Loading response...</div>
            </div>
            <div v-else class="flex items-center justify-center h-32 text-sm text-gray-400">
              Select a config and submit a query
            </div>
          </div>
        </div>

        <!-- Right Panel -->
        <div class="flex flex-col">
          <div class="bg-white border-b border-gray-200 px-4 py-3">
            <label class="block text-xs font-medium text-gray-500 mb-1">Config B</label>
            <select
              v-model="configIdB"
              class="w-full px-3 py-2 border border-gray-300 rounded-md bg-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              :disabled="isLoading"
            >
              <option value="" disabled>Select a configuration</option>
              <option
                v-for="config in readyConfigs"
                :key="config.id"
                :value="config.id"
              >
                {{ config.name }}
              </option>
            </select>
          </div>
          <div class="flex-1 overflow-y-auto p-4">
            <ComparisonResult
              v-if="resultB"
              :result="resultB"
              label="B"
            />
            <div v-else-if="isLoading && configIdB" class="flex items-center justify-center h-32">
              <div class="text-sm text-gray-500">Loading response...</div>
            </div>
            <div v-else class="flex items-center justify-center h-32 text-sm text-gray-400">
              Select a config and submit a query
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import apiClient from '@/api/client'
import ComparisonResult from '@/components/comparison/ComparisonResult.vue'
import { errorMessage } from '@/api/errors'

interface ComparisonResultData {
  response: string
  responseTime: number
  sources: Array<{
    content: string
    score: number
    metadata: { file_name?: string;[key: string]: unknown }
  }>
  tokenCount: number | null
  error?: string
}

const router = useRouter()
const authStore = useAuthStore()
const configStore = useConfigStore()

const query = ref('')
const configIdA = ref('')
const configIdB = ref('')
const resultA = ref<ComparisonResultData | null>(null)
const resultB = ref<ComparisonResultData | null>(null)
const isLoading = ref(false)

const readyConfigs = computed(() =>
  configStore.configs.filter(
    (c) => c.status === 'ready' || c.status === 'completed' || c.status === undefined
  )
)

const canSubmit = computed(() =>
  query.value.trim() && configIdA.value && configIdB.value && !isLoading.value
)

onMounted(() => {
  configStore.fetchConfigs()
})

async function queryConfig(configId: string): Promise<ComparisonResultData> {
  const startTime = performance.now()
  try {
    const response = await apiClient.post('/v1/query', {
      query: query.value,
      config_id: configId,
      include_sources: true,
      include_debug: true,
    })
    const elapsed = Math.round(performance.now() - startTime)
    const data = response.data
    return {
      response: data.answer || data.response || '',
      responseTime: elapsed,
      sources: data.sources || [],
      tokenCount: data.metadata?.tokens_used ?? data.debug?.tokens_used ?? null,
    }
  } catch (err) {
    const elapsed = Math.round(performance.now() - startTime)
    return {
      response: '',
      responseTime: elapsed,
      sources: [],
      tokenCount: null,
      error: errorMessage(err, 'Request failed'),
    }
  }
}

async function submitQuery() {
  if (!canSubmit.value) return

  isLoading.value = true
  resultA.value = null
  resultB.value = null

  const [resA, resB] = await Promise.all([
    queryConfig(configIdA.value),
    queryConfig(configIdB.value),
  ])

  resultA.value = resA
  resultB.value = resB
  isLoading.value = false
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>
