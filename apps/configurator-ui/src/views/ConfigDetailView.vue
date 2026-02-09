<template>
  <div>
    <!-- Header -->
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center gap-4">
          <button @click="goBack" class="text-gray-600 hover:text-gray-900">
            ← Back
          </button>
          <h1 class="text-2xl font-bold text-gray-900">
            {{ config?.name || 'Configuration Details' }}
          </h1>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div v-if="configStore.loading" class="text-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
        <p class="mt-4 text-gray-600">Loading...</p>
      </div>

      <div v-else-if="config" class="space-y-6">
        <!-- Status Card -->
        <div class="bg-white rounded-lg shadow p-6">
          <div class="flex justify-between items-center">
            <div>
              <h2 class="text-lg font-semibold">Status</h2>
              <p class="text-sm text-gray-600 mt-1">{{ config.description }}</p>
            </div>
            <div class="flex gap-4">
              <button
                @click="runIngestion"
                :disabled="['processing', 'running', 'pending'].includes(ingestionStatus?.status ?? '')"
                class="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
              >
                {{ ['processing', 'running', 'pending'].includes(ingestionStatus?.status ?? '') ? 'Processing...' : 'Run Ingestion' }}
              </button>
              <button
                @click="editConfig"
                class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Edit
              </button>
            </div>
          </div>
        </div>

        <!-- Ingestion Progress -->
        <div v-if="ingestionStatus" class="bg-white rounded-lg shadow p-6">
          <h2 class="text-lg font-semibold mb-4">Ingestion Progress</h2>
          
          <div class="mb-4">
            <div class="flex justify-between text-sm mb-1">
              <span>{{ ingestionStatus.current_step }}</span>
              <span>{{ ingestionStatus.progress }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div
                class="bg-primary-600 h-2 rounded-full transition-all"
                :style="{ width: ingestionStatus.progress + '%' }"
              ></div>
            </div>
          </div>

          <div class="grid grid-cols-4 gap-4 text-center">
            <div class="bg-gray-50 rounded p-3">
              <div class="text-2xl font-bold">{{ ingestionStatus.processed_files || 0 }}</div>
              <div class="text-sm text-gray-600">Processed</div>
            </div>
            <div class="bg-gray-50 rounded p-3">
              <div class="text-2xl font-bold">{{ ingestionStatus.failed_files || 0 }}</div>
              <div class="text-sm text-gray-600">Failed</div>
            </div>
            <div class="bg-gray-50 rounded p-3">
              <div class="text-2xl font-bold">{{ ingestionStatus.total_chunks || 0 }}</div>
              <div class="text-sm text-gray-600">Chunks</div>
            </div>
            <div class="bg-gray-50 rounded p-3">
              <div class="text-xl font-bold capitalize">{{ ingestionStatus.status }}</div>
              <div class="text-sm text-gray-600">Status</div>
            </div>
          </div>
        </div>

        <!-- Config Summary -->
        <div class="bg-white rounded-lg shadow p-6">
          <h2 class="text-lg font-semibold mb-4">Configuration Summary</h2>
          
          <div class="grid md:grid-cols-2 gap-6">
            <div>
              <h3 class="font-medium text-gray-900 mb-2">Data Source</h3>
              <p class="text-sm text-gray-600">Type: {{ config.data_source?.type }}</p>
              <p class="text-sm text-gray-600">Path: {{ config.data_source?.base_path }}</p>
              <p class="text-sm text-gray-600">Folders: {{ config.data_source?.folders?.length || 0 }}</p>
            </div>

            <div>
              <h3 class="font-medium text-gray-900 mb-2">Models</h3>
              <p class="text-sm text-gray-600">LLM: {{ config.models?.llm?.provider }} - {{ config.models?.llm?.model_name }}</p>
              <p class="text-sm text-gray-600">Embedding: {{ config.models?.embedding?.provider }} - {{ config.models?.embedding?.model_name }}</p>
            </div>

            <div>
              <h3 class="font-medium text-gray-900 mb-2">Retrieval</h3>
              <p class="text-sm text-gray-600">Method: {{ config.retrieval?.method }}</p>
              <p class="text-sm text-gray-600">Top K: {{ config.retrieval?.vector?.top_k }}</p>
              <p class="text-sm text-gray-600">Chunk Size: {{ config.chunking?.chunk_size }}</p>
            </div>

            <div>
              <h3 class="font-medium text-gray-900 mb-2">Agent</h3>
              <p class="text-sm text-gray-600">Template: {{ config.agent?.template }}</p>
              <p class="text-sm text-gray-600">Max Iterations: {{ config.agent?.max_iterations }}</p>
              <p class="text-sm text-gray-600">LLM Judge: {{ config.agent?.enable_judge ? 'Enabled' : 'Disabled' }}</p>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="text-center py-12">
        <p class="text-gray-600">Configuration not found</p>
        <button @click="goBack" class="mt-4 text-primary-600 hover:text-primary-800">
          Back to Dashboard
        </button>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useConfigStore } from '@/stores/config'
import { configApi, ingestApi } from '@/api/configs'
import type { RAGConfig, IngestionStatus } from '@/types'

const router = useRouter()
const route = useRoute()
const configStore = useConfigStore()

const config = ref<RAGConfig | null>(null)
const ingestionStatus = ref<IngestionStatus | null>(null)
const pollInterval = ref<number | null>(null)

const configId = route.params.id as string

onMounted(() => {
  loadConfig()
})

onUnmounted(() => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
  }
})

async function loadConfig() {
  try {
    config.value = await configApi.get(configId)
    await checkIngestionStatus()
  } catch (err) {
    console.error('Failed to load config:', err)
  }
}

async function checkIngestionStatus() {
  try {
    ingestionStatus.value = await ingestApi.status(configId)
    
    // Poll if processing or running
    const activeStatuses = ['processing', 'running', 'pending']
    if (activeStatuses.includes(ingestionStatus.value?.status ?? '')) {
      if (!pollInterval.value) {
        pollInterval.value = window.setInterval(checkIngestionStatus, 2000)
      }
    } else {
      if (pollInterval.value) {
        clearInterval(pollInterval.value)
        pollInterval.value = null
      }
    }
  } catch (err) {
    // No ingestion started yet
  }
}

async function runIngestion() {
  try {
    await ingestApi.start(configId)
    await checkIngestionStatus()
  } catch (err) {
    console.error('Failed to start ingestion:', err)
  }
}

function editConfig() {
  router.push(`/wizard/${configId}`)
}

function goBack() {
  router.push('/')
}
</script>
