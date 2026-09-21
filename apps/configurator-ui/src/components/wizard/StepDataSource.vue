<template>
  <div class="space-y-6">
    <!-- Config Name -->
    <div class="space-y-2">
      <label class="block text-sm font-medium text-gray-700">
        Configuration Name <span class="text-red-500">*</span>
      </label>
      <input
        v-model="config.name"
        type="text"
        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        placeholder="Enter a name for this configuration"
        @blur="validateStep"
      />
      <p v-if="errors.name" class="text-sm text-red-600">{{ errors.name }}</p>
    </div>

    <!-- Config Description -->
    <div class="space-y-2">
      <label class="block text-sm font-medium text-gray-700">
        Description
      </label>
      <textarea
        v-model="config.description"
        rows="2"
        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        placeholder="Optional description of this configuration"
      />
    </div>

    <!-- Data Source Type -->
    <div class="space-y-2">
      <label class="block text-sm font-medium text-gray-700">
        Data Source Type
      </label>
      <div class="flex gap-4">
        <button
          @click="setDataSourceType('local')"
          :class="[
            'flex-1 p-4 border-2 rounded-lg text-center transition-all',
            config.data_source.type === 'local'
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-200 hover:border-gray-300'
          ]"
        >
          <div class="text-2xl mb-2">📁</div>
          <div class="font-medium text-gray-900">Local Files</div>
          <div class="text-xs text-gray-500 mt-1">Folder scanning</div>
        </button>
        <button
          @click="setDataSourceType('s3')"
          :class="[
            'flex-1 p-4 border-2 rounded-lg text-center transition-all',
            config.data_source.type === 's3'
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-200 hover:border-gray-300'
          ]"
        >
          <div class="text-2xl mb-2">☁️</div>
          <div class="font-medium text-gray-900">AWS S3</div>
          <div class="text-xs text-gray-500 mt-1">S3 bucket</div>
        </button>
      </div>
    </div>

    <!-- Local Folders Section -->
    <div v-if="config.data_source.type === 'local'" class="space-y-4">
      <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h4 class="font-medium text-gray-900 mb-2">Base Path</h4>
        <div class="flex gap-2">
          <input
            v-model="basePath"
            type="text"
            class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
            placeholder="Click Browse to select a folder, or type a path"
          />
          <button
            @click="showBrowseModal = true"
            class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-50 flex items-center gap-1"
          >
            <span>📂</span>
            <span>Browse</span>
          </button>
          <button
            @click="refreshFolders"
            :disabled="scanning || !basePath"
            class="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="scanning">Scanning...</span>
            <span v-else>Scan</span>
          </button>
        </div>
        <p class="text-xs text-gray-500 mt-1">
          Browse your local folders or enter an absolute path, then click Scan to discover contents
        </p>
      </div>

      <!-- Folder Tree -->
      <div v-if="folderStructure.length > 0" class="bg-white border border-gray-200 rounded-lg">
        <div class="p-3 bg-gray-50 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <h4 class="font-medium text-gray-900">Select Folders</h4>
            <div class="flex gap-2">
              <button
                @click="selectAll"
                class="text-xs text-primary-600 hover:text-primary-700"
              >
                Select All
              </button>
              <span class="text-gray-300">|</span>
              <button
                @click="deselectAll"
                class="text-xs text-gray-600 hover:text-gray-700"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
        <div class="p-3 max-h-64 overflow-y-auto">
          <FolderTreeItem
            v-for="folder in folderStructure"
            :key="folder.path"
            :item="folder"
            :selected="selectedFolderPaths"
            @toggle="toggleFolder"
          />
        </div>
        <div class="p-2 bg-gray-50 border-t border-gray-200 text-sm text-gray-600">
          {{ (config.data_source.folders || []).length }} folder(s) selected
        </div>
      </div>

      <!-- No Folders Message -->
      <div v-else-if="scanAttempted && !scanning" class="text-center py-8 bg-gray-50 rounded-lg">
        <div class="text-4xl mb-2">📂</div>
        <p class="text-gray-600">No folders found. Enter a path and click Scan.</p>
      </div>
    </div>

    <!-- S3 Configuration -->
    <div v-else class="space-y-4">
      <div class="space-y-2">
        <label class="block text-sm font-medium text-gray-700">
          S3 Bucket <span class="text-red-500">*</span>
        </label>
        <input
          v-model="config.data_source.bucket"
          type="text"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          placeholder="my-bucket-name"
          @blur="validateStep"
        />
      </div>
      <div class="space-y-2">
        <label class="block text-sm font-medium text-gray-700">
          Prefix (Optional)
        </label>
        <input
          v-model="config.data_source.prefix"
          type="text"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          placeholder="path/to/documents/"
        />
        <p class="text-xs text-gray-500">Filter objects with this prefix</p>
      </div>
      <div class="space-y-2">
        <label class="block text-sm font-medium text-gray-700">
          AWS Region
        </label>
        <input
          v-model="config.data_source.region"
          type="text"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          placeholder="us-east-1"
        />
      </div>
    </div>

    <!-- File Patterns Info -->
    <div v-if="config.data_source.folders && config.data_source.folders.length > 0" class="p-3 bg-gray-50 rounded-lg">
      <p class="text-sm text-gray-600">
        <span class="font-medium">File patterns:</span> All file types will be included (* pattern).
        You can customize patterns per folder in the folder settings.
      </p>
    </div>

    <!-- Validation Summary -->
    <div v-if="hasErrors" class="p-3 bg-red-50 border border-red-200 rounded-lg">
      <h4 class="text-sm font-medium text-red-800 mb-1">Please fix the following:</h4>
      <ul class="text-sm text-red-600 list-disc list-inside">
        <li v-if="errors.name">Enter a configuration name</li>
        <li v-if="errors.basePath && config.data_source.type === 'local'">Enter a valid base path</li>
        <li v-if="errors.folders">Select at least one folder</li>
      </ul>
    </div>

    <!-- Browse Modal -->
    <FolderBrowseModal
      :show="showBrowseModal"
      @close="showBrowseModal = false"
      @select="onBrowseSelect"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed, onMounted } from 'vue'
import { useWizardStore } from '@/stores/wizard'
import { configApi } from '@/api/configs'
import FolderTreeItem from './FolderTreeItem.vue'
import FolderBrowseModal from './FolderBrowseModal.vue'
import type { FolderStructure, FolderConfig } from '@/types'

const wizardStore = useWizardStore()
const config = wizardStore.config

const basePath = computed({
  get: () => config.data_source?.base_path || '',
  set: (val: string) => {
    if (config.data_source) {
      config.data_source.base_path = val
    }
  },
})
const folderStructure = ref<FolderStructure[]>([])
const scanning = ref(false)
const scanAttempted = ref(false)
const showBrowseModal = ref(false)
const errors = reactive({
  name: '',
  basePath: '',
  folders: '',
  fileTypes: ''
})

// Computed to get selected folder paths for the tree component
const selectedFolderPaths = computed(() => {
  return (config.data_source?.folders || []).map(f => f.path)
})

const hasErrors = computed(() => {
  return Object.values(errors).some(e => e !== '')
})

function setDataSourceType(type: 'local' | 's3') {
  if (!config.data_source) {
    config.data_source = {
      type,
      base_path: '',
      folders: [],
      has_multimodal: false
    }
  } else {
    config.data_source.type = type
  }
  validateStep()
}

function toggleFolder(path: string, selected: boolean) {
  const folders = config.data_source.folders || []
  if (selected) {
    // Find the folder structure item to get details
    const findFolder = (items: FolderStructure[], targetPath: string): FolderStructure | null => {
      for (const item of items) {
        if (item.path === targetPath) return item
        if (item.children) {
          const found = findFolder(item.children, targetPath)
          if (found) return found
        }
      }
      return null
    }
    const folderItem = findFolder(folderStructure.value, path)
    if (folderItem && !folders.some(f => f.path === path)) {
      folders.push({
        path: path,
        name: folderItem.name,
        detected_types: [],
        allowed_roles: ['*'],
        recursive: true,
        file_patterns: ['*'],
        file_count: folderItem.file_count || 0
      })
    }
  } else {
    const index = folders.findIndex(f => f.path === path)
    if (index !== -1) {
      folders.splice(index, 1)
    }
  }
  config.data_source.folders = folders
  validateStep()
}

function selectAll() {
  const allFolders: FolderConfig[] = []
  const collectFolders = (items: FolderStructure[]) => {
    items.forEach(item => {
      allFolders.push({
        path: item.path,
        name: item.name,
        detected_types: [],
        allowed_roles: ['*'],
        recursive: true,
        file_patterns: ['*'],
        file_count: item.file_count || 0
      })
      if (item.children) {
        collectFolders(item.children)
      }
    })
  }
  collectFolders(folderStructure.value)
  config.data_source.folders = allFolders
  validateStep()
}

function deselectAll() {
  config.data_source.folders = []
  validateStep()
}

async function refreshFolders() {
  if (!basePath.value || scanning.value) return

  scanning.value = true
  scanAttempted.value = true

  try {
    const structure = await configApi.scanFolders(basePath.value)
    folderStructure.value = structure

    // Auto-select first-level folders if editing or new
    if (!config.data_source.folders || config.data_source.folders.length === 0) {
      config.data_source.folders = structure.map(f => ({
        path: f.path,
        name: f.name,
        detected_types: [],
        allowed_roles: ['*'],
        recursive: true,
        file_patterns: ['*'],
        file_count: f.file_count || 0
      }))
    }

    validateStep()
  } catch (err) {
    console.error('Failed to scan folders:', err)
    folderStructure.value = []
  } finally {
    scanning.value = false
  }
}

function onBrowseSelect(path: string) {
  basePath.value = path
  // Auto-trigger scan when folder is selected via browse
  refreshFolders()
}

function validateStep() {
  errors.name = !config.name || !config.name.trim() ? 'Name is required' : ''

  if (config.data_source.type === 'local') {
    errors.basePath = !basePath.value ? 'Base path is required' : ''
    errors.folders = !config.data_source.folders || config.data_source.folders.length === 0
      ? 'Select at least one folder'
      : ''
  } else {
    errors.basePath = ''
    errors.folders = ''
  }

  // File types validation removed as it's per-folder now
  errors.fileTypes = ''

  const isValid = !errors.name && !errors.basePath && !errors.folders
  wizardStore.stepValidation[0] = isValid
}

// Validate on mount
validateStep()

// Re-populate folder tree if returning to this step with existing data
onMounted(() => {
  if (config.data_source?.folders?.length > 0 && basePath.value) {
    scanAttempted.value = true
    refreshFolders()
  }
})

// Watch for changes
watch(() => config.name, validateStep)
watch(() => config.data_source, validateStep, { deep: true })
</script>
