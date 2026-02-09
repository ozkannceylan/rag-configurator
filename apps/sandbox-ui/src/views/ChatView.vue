<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-4">
        <h1 class="text-xl font-bold text-gray-900">RAG Sandbox</h1>
        <ConfigSelector />
      </div>
      <div class="flex items-center gap-3">
        <button
          v-if="configStore.selectedConfig?.rbac?.enabled"
          class="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Role: {{ selectedRole }}
        </button>
        <button
          @click="handleLogout"
          class="px-3 py-1.5 text-sm text-red-600 hover:text-red-700"
        >
          Logout
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Chat Area -->
      <div class="flex-1 flex flex-col min-w-0">
        <ChatContainer class="flex-1" />
      </div>

      <!-- Sidebar -->
      <aside class="w-96 bg-white border-l border-gray-200 flex flex-col overflow-hidden">
        <div class="flex border-b border-gray-200">
          <button
            @click="activeTab = 'sources'"
            :class="[
              'flex-1 px-4 py-3 text-sm font-medium text-center',
              activeTab === 'sources'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-600 hover:text-gray-900'
            ]"
          >
            Sources ({{ chatStore.currentSources.length }})
          </button>
          <button
            @click="activeTab = 'debug'"
            :class="[
              'flex-1 px-4 py-3 text-sm font-medium text-center',
              activeTab === 'debug'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-600 hover:text-gray-900'
            ]"
          >
            Debug ({{ chatStore.currentSteps.length }})
          </button>
        </div>

        <div class="flex-1 overflow-y-auto">
          <SourcesPanel v-if="activeTab === 'sources'" />
          <DebugPanel v-else />
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import { useChatStore } from '@/stores/chat'
import ConfigSelector from '@/components/sidebar/ConfigSelector.vue'
import ChatContainer from '@/components/chat/ChatContainer.vue'
import SourcesPanel from '@/components/sidebar/SourcesPanel.vue'
import DebugPanel from '@/components/sidebar/DebugPanel.vue'

const router = useRouter()
const authStore = useAuthStore()
const configStore = useConfigStore()
const chatStore = useChatStore()

const activeTab = ref<'sources' | 'debug'>('sources')
const selectedRole = ref('user')

onMounted(() => {
  configStore.fetchConfigs()
})

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>
