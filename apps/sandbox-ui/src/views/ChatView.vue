<template>
  <div class="h-screen flex flex-col bg-gray-50">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shrink-0">
      <div class="flex items-center gap-4">
        <h1 class="text-xl font-bold text-gray-900">RAG Sandbox</h1>
        <ConfigSelector />
      </div>
      <div class="flex items-center gap-3">
        <div v-if="configStore.selectedConfig?.rbac?.enabled" class="relative">
          <button
            @click="showRoleSelector = !showRoleSelector"
            class="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-1"
          >
            Role: {{ selectedRole }}
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
          </button>
          <div
            v-if="showRoleSelector"
            class="absolute right-0 mt-1 w-48 bg-white border border-gray-200 rounded-md shadow-lg z-10"
          >
            <button
              v-for="role in availableRoles"
              :key="role"
              @click="selectedRole = role; showRoleSelector = false"
              :class="[
                'block w-full text-left px-4 py-2 text-sm hover:bg-gray-50',
                role === selectedRole ? 'bg-primary-50 text-primary-700 font-medium' : 'text-gray-700'
              ]"
            >
              {{ role }}
            </button>
          </div>
        </div>
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
          <button
            @click="activeTab = 'retrieval'"
            :class="[
              'flex-1 px-4 py-3 text-sm font-medium text-center',
              activeTab === 'retrieval'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-600 hover:text-gray-900'
            ]"
          >
            Retrieval
          </button>
        </div>

        <div class="flex-1 overflow-y-auto">
          <SourcesPanel v-if="activeTab === 'sources'" />
          <DebugPanel v-else-if="activeTab === 'debug'" />
          <RetrievalDebugger v-else />
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import { useChatStore } from '@/stores/chat'
import ConfigSelector from '@/components/sidebar/ConfigSelector.vue'
import ChatContainer from '@/components/chat/ChatContainer.vue'
import SourcesPanel from '@/components/sidebar/SourcesPanel.vue'
import DebugPanel from '@/components/sidebar/DebugPanel.vue'
import RetrievalDebugger from '@/components/sidebar/RetrievalDebugger.vue'

const router = useRouter()
const authStore = useAuthStore()
const configStore = useConfigStore()
const chatStore = useChatStore()

const activeTab = ref<'sources' | 'debug' | 'retrieval'>('sources')
const selectedRole = ref('user')
const showRoleSelector = ref(false)

const availableRoles = computed(() => {
  const roles = configStore.selectedConfig?.rbac?.roles
  if (!roles || roles.length === 0) return ['user']
  return roles
})

// Close role selector when clicking outside
function handleClickOutside(e: MouseEvent) {
  if (showRoleSelector.value) {
    const target = e.target as HTMLElement
    if (!target.closest('.relative')) {
      showRoleSelector.value = false
    }
  }
}

onMounted(() => {
  configStore.fetchConfigs()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>
