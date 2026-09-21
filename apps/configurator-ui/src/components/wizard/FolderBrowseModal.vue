<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/50" @click="close"></div>

    <!-- Modal -->
    <div class="relative bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 flex flex-col max-h-[80vh]">
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200">
        <h3 class="text-lg font-semibold text-gray-900">Browse Folders</h3>
        <button @click="close" class="text-gray-400 hover:text-gray-600 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Current Path Breadcrumb -->
      <div class="px-5 py-2 bg-gray-50 border-b border-gray-200 text-sm">
        <div class="flex items-center gap-1 text-gray-600 overflow-x-auto">
          <button
            @click="navigateTo('')"
            class="hover:text-primary-600 font-medium shrink-0"
          >
            🏠 Roots
          </button>
          <template v-if="currentPath && currentPath !== '/'">
            <span class="text-gray-400 shrink-0">/</span>
            <span class="truncate text-gray-800 font-medium">{{ currentPath }}</span>
          </template>
        </div>
      </div>

      <!-- Folder List -->
      <div class="flex-1 overflow-y-auto min-h-[200px] max-h-[400px]">
        <!-- Loading -->
        <div v-if="loading" class="flex items-center justify-center py-12">
          <div class="flex items-center gap-3 text-gray-500">
            <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z"></path>
            </svg>
            <span>Loading...</span>
          </div>
        </div>

        <!-- Error -->
        <div v-else-if="error" class="px-5 py-8 text-center">
          <div class="text-red-500 text-3xl mb-2">⚠️</div>
          <p class="text-sm text-red-600">{{ error }}</p>
          <button @click="navigateTo(currentPath)" class="mt-3 text-sm text-primary-600 hover:underline">
            Retry
          </button>
        </div>

        <!-- Empty -->
        <div v-else-if="entries.length === 0" class="px-5 py-8 text-center">
          <div class="text-gray-400 text-3xl mb-2">📂</div>
          <p class="text-sm text-gray-500">No subfolders found</p>
        </div>

        <!-- Entries -->
        <div v-else class="divide-y divide-gray-100">
          <!-- Back button -->
          <button
            v-if="parentPath !== null && parentPath !== undefined"
            @click="navigateTo(parentPath)"
            class="w-full flex items-center gap-3 px-5 py-3 hover:bg-gray-50 transition-colors text-left"
          >
            <span class="text-lg">⬆️</span>
            <span class="text-sm text-gray-600 font-medium">.. (Go Back)</span>
          </button>

          <!-- Folder entries -->
          <button
            v-for="entry in entries"
            :key="entry.path"
            @click="onEntryClick(entry)"
            :class="[
              'w-full flex items-center gap-3 px-5 py-3 transition-colors text-left',
              selectedPath === entry.path
                ? 'bg-primary-50 border-l-4 border-primary-500'
                : 'hover:bg-gray-50 border-l-4 border-transparent'
            ]"
          >
            <span class="text-lg shrink-0">📁</span>
            <div class="flex-1 min-w-0">
              <span class="text-sm font-medium text-gray-900 block truncate">{{ entry.name }}</span>
            </div>
            <span v-if="entry.has_children" class="text-gray-400 shrink-0">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </span>
          </button>
        </div>
      </div>

      <!-- Footer with Selected Path + Actions -->
      <div class="px-5 py-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
        <div v-if="selectedPath" class="mb-3 p-2 bg-white border border-gray-200 rounded-md">
          <p class="text-xs text-gray-500 mb-1">Selected folder:</p>
          <p class="text-sm text-gray-900 font-medium truncate">{{ selectedPath }}</p>
        </div>
        <div class="flex gap-3 justify-end">
          <button
            v-if="currentPath && currentPath !== '/'"
            @click="selectCurrent"
            class="px-4 py-2 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-200 rounded-lg hover:bg-primary-100 transition-colors"
          >
            Use Current Folder
          </button>
          <button
            @click="close"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            @click="confirmSelection"
            :disabled="!selectedPath"
            class="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Select
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { configApi, type BrowseEntry } from '@/api/configs'
import { errorMessage } from '@/api/errors'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'select', path: string): void
}>()

const loading = ref(false)
const error = ref('')
const currentPath = ref('')
const parentPath = ref<string | null>(null)
const entries = ref<BrowseEntry[]>([])
const selectedPath = ref('')

// Load root entries when modal opens
watch(() => props.show, (isOpen) => {
  if (isOpen) {
    selectedPath.value = ''
    navigateTo('')
  }
})

async function navigateTo(path: string) {
  loading.value = true
  error.value = ''

  try {
    const response = await configApi.browseFolders(path)
    currentPath.value = response.current_path
    parentPath.value = response.parent_path
    entries.value = response.entries
  } catch (err) {
    error.value = errorMessage(err, 'Failed to browse')
    entries.value = []
  } finally {
    loading.value = false
  }
}

function onEntryClick(entry: BrowseEntry) {
  if (selectedPath.value === entry.path) {
    // Double-click behavior: navigate into folder
    navigateTo(entry.path)
    selectedPath.value = ''
  } else {
    selectedPath.value = entry.path
  }
}

function selectCurrent() {
  emit('select', currentPath.value)
  emit('close')
}

function confirmSelection() {
  if (selectedPath.value) {
    emit('select', selectedPath.value)
    emit('close')
  }
}

function close() {
  emit('close')
}
</script>
