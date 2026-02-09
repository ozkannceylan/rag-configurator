<template>
  <div>
    <!-- Header -->
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex justify-between items-center">
          <h1 class="text-2xl font-bold text-gray-900">RAG Configurator</h1>
          <div class="flex items-center gap-4">
            <span v-if="authStore.user" class="text-sm text-gray-600">
              {{ authStore.user.name }}
            </span>
            <button
              @click="handleLogout"
              class="text-sm text-red-600 hover:text-red-800"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Actions -->
      <div class="mb-8">
        <button
          @click="createNewConfig"
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
        >
          + Create New Config
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="configStore.loading" class="text-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
        <p class="mt-4 text-gray-600">Loading configurations...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="configStore.error" class="text-center py-12">
        <p class="text-red-600">{{ configStore.error }}</p>
        <button
          @click="configStore.fetchConfigs()"
          class="mt-4 text-primary-600 hover:text-primary-800"
        >
          Retry
        </button>
      </div>

      <!-- Empty State -->
      <div v-else-if="configStore.configs.length === 0" class="text-center py-12 bg-white rounded-lg shadow">
        <h3 class="text-lg font-medium text-gray-900 mb-2">No configurations yet</h3>
        <p class="text-gray-600 mb-4">Create your first RAG configuration to get started.</p>
        <button
          @click="createNewConfig"
          class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700"
        >
          Create Config
        </button>
      </div>

      <!-- Config List -->
      <div v-else class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="config in configStore.configs"
          :key="config.id"
          class="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
        >
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="text-lg font-semibold text-gray-900">{{ config.name }}</h3>
              <p v-if="config.description" class="text-sm text-gray-600 mt-1">
                {{ config.description }}
              </p>
            </div>
            <span
              :class="[
                'px-2 py-1 text-xs rounded-full',
                config.status === 'ready' ? 'bg-green-100 text-green-800' :
                config.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                config.status === 'error' ? 'bg-red-100 text-red-800' :
                'bg-gray-100 text-gray-800'
              ]"
            >
              {{ config.status || 'draft' }}
            </span>
          </div>

          <div class="text-sm text-gray-600 mb-4">
            <p>Data Source: {{ config.data_source?.type }}</p>
            <p>Agent: {{ config.agent?.template }}</p>
            <p>Updated: {{ formatDate(config.updated_at) }}</p>
          </div>

          <div class="flex flex-wrap gap-2">
            <button
              @click="editConfig(config.id!)"
              class="text-sm text-primary-600 hover:text-primary-800"
            >
              Edit
            </button>
            <button
              @click="viewConfig(config.id!)"
              class="text-sm text-gray-600 hover:text-gray-800"
            >
              View
            </button>
            <button
              @click="duplicateConfig(config.id!)"
              class="text-sm text-gray-600 hover:text-gray-800"
            >
              Duplicate
            </button>
            <button
              @click="deleteConfig(config.id!)"
              class="text-sm text-red-600 hover:text-red-800"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'

const router = useRouter()
const authStore = useAuthStore()
const configStore = useConfigStore()

onMounted(() => {
  configStore.fetchConfigs()
})

function createNewConfig() {
  router.push('/wizard')
}

function editConfig(id: string) {
  router.push(`/wizard/${id}`)
}

function viewConfig(id: string) {
  router.push(`/config/${id}`)
}

async function duplicateConfig(id: string) {
  await configStore.duplicateConfig(id)
}

async function deleteConfig(id: string) {
  if (confirm('Are you sure you want to delete this configuration?')) {
    await configStore.deleteConfig(id)
  }
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

function formatDate(date?: string) {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString()
}
</script>
