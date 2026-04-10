<template>
  <div>
    <!-- Header -->
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <router-link to="/" class="text-gray-600 hover:text-gray-900">
              &larr; Back
            </router-link>
            <h1 class="text-2xl font-bold text-gray-900">Template Marketplace</h1>
          </div>
          <div class="flex items-center gap-3">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search templates..."
              class="px-4 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="flex gap-8">
        <!-- Category Filter Sidebar -->
        <div class="w-48 flex-shrink-0">
          <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">Categories</h3>
          <nav class="space-y-1">
            <button
              v-for="cat in categories"
              :key="cat.value"
              @click="selectedCategory = cat.value"
              :class="[
                'w-full text-left px-3 py-2 rounded-md text-sm transition-colors',
                selectedCategory === cat.value
                  ? 'bg-primary-50 text-primary-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              ]"
            >
              {{ cat.label }}
            </button>
          </nav>
        </div>

        <!-- Templates Grid -->
        <div class="flex-1">
          <!-- Loading -->
          <div v-if="loading" class="flex items-center justify-center py-16">
            <div class="text-sm text-gray-500">Loading templates...</div>
          </div>

          <!-- Templates -->
          <div v-else-if="templates.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div
              v-for="template in templates"
              :key="template.id"
              class="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow cursor-pointer"
              @click="openPreview(template)"
            >
              <div class="flex items-start justify-between mb-3">
                <h3 class="text-sm font-semibold text-gray-900 line-clamp-1">{{ template.name }}</h3>
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-100 text-primary-800">
                  {{ template.category }}
                </span>
              </div>
              <p class="text-xs text-gray-500 mb-3 line-clamp-2">
                {{ template.description || 'No description' }}
              </p>
              <div class="flex items-center justify-between">
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="tag in template.tags.slice(0, 3)"
                    :key="tag"
                    class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-600"
                  >
                    {{ tag }}
                  </span>
                </div>
                <span class="text-xs text-gray-400">
                  {{ template.usage_count }} uses
                </span>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-else class="text-center py-16">
            <h3 class="text-lg font-medium text-gray-900 mb-1">No templates found</h3>
            <p class="text-sm text-gray-500">
              {{ searchQuery ? 'Try a different search term.' : 'No templates available in this category.' }}
            </p>
          </div>

          <!-- Pagination -->
          <div v-if="total > pageSize" class="mt-6 flex items-center justify-center gap-2">
            <button
              @click="page > 1 && changePage(page - 1)"
              :disabled="page <= 1"
              class="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              Previous
            </button>
            <span class="text-sm text-gray-600">
              Page {{ page }} of {{ Math.ceil(total / pageSize) }}
            </span>
            <button
              @click="page < Math.ceil(total / pageSize) && changePage(page + 1)"
              :disabled="page >= Math.ceil(total / pageSize)"
              class="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- Preview Modal -->
    <div
      v-if="previewTemplate"
      class="fixed inset-0 z-50 overflow-y-auto"
      @click.self="previewTemplate = null"
    >
      <div class="flex min-h-full items-center justify-center p-4">
        <div class="fixed inset-0 bg-black bg-opacity-25" @click="previewTemplate = null" />
        <div class="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6">
          <div class="flex items-start justify-between mb-4">
            <div>
              <h2 class="text-lg font-semibold text-gray-900">{{ previewTemplate.name }}</h2>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-100 text-primary-800 mt-1">
                {{ previewTemplate.category }}
              </span>
            </div>
            <button
              @click="previewTemplate = null"
              class="text-gray-400 hover:text-gray-600"
            >
              <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          <p class="text-sm text-gray-600 mb-4">{{ previewTemplate.description || 'No description' }}</p>

          <div v-if="previewTemplate.tags.length" class="flex flex-wrap gap-2 mb-4">
            <span
              v-for="tag in previewTemplate.tags"
              :key="tag"
              class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-600"
            >
              {{ tag }}
            </span>
          </div>

          <div class="text-xs text-gray-500 mb-4">
            {{ previewTemplate.usage_count }} uses
          </div>

          <!-- Config preview -->
          <div v-if="previewDetail" class="border border-gray-200 rounded-lg p-4 mb-6 bg-gray-50">
            <h3 class="text-sm font-medium text-gray-900 mb-3">Configuration Preview</h3>
            <div class="space-y-2 text-xs">
              <div v-if="previewDetail.config_snapshot?.models?.llm" class="flex">
                <span class="text-gray-400 w-24">LLM:</span>
                <span class="text-gray-700">
                  {{ previewDetail.config_snapshot.models.llm.provider }} / {{ previewDetail.config_snapshot.models.llm.model_name }}
                </span>
              </div>
              <div v-if="previewDetail.config_snapshot?.models?.embedding" class="flex">
                <span class="text-gray-400 w-24">Embedding:</span>
                <span class="text-gray-700">
                  {{ previewDetail.config_snapshot.models.embedding.provider }} / {{ previewDetail.config_snapshot.models.embedding.model_name }}
                </span>
              </div>
              <div v-if="previewDetail.config_snapshot?.agent" class="flex">
                <span class="text-gray-400 w-24">Agent:</span>
                <span class="text-gray-700">{{ previewDetail.config_snapshot.agent.template }}</span>
              </div>
              <div v-if="previewDetail.config_snapshot?.retrieval" class="flex">
                <span class="text-gray-400 w-24">Retrieval:</span>
                <span class="text-gray-700">{{ previewDetail.config_snapshot.retrieval.method }}</span>
              </div>
              <div v-if="previewDetail.config_snapshot?.chunking" class="flex">
                <span class="text-gray-400 w-24">Chunking:</span>
                <span class="text-gray-700">
                  {{ previewDetail.config_snapshot.chunking.strategy }} ({{ previewDetail.config_snapshot.chunking.chunk_size }} tokens)
                </span>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-3">
            <button
              @click="previewTemplate = null"
              class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Close
            </button>
            <button
              @click="useTemplate"
              :disabled="cloning"
              class="px-4 py-2 bg-primary-600 text-white rounded-md text-sm font-medium hover:bg-primary-700 disabled:opacity-50"
            >
              {{ cloning ? 'Cloning...' : 'Use Template' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/api/client'

interface TemplateSummary {
  id: string
  name: string
  description: string
  category: string
  tags: string[]
  created_by: string
  created_at: string
  usage_count: number
}

interface TemplateDetail extends TemplateSummary {
  config_snapshot: Record<string, any>
}

const router = useRouter()

const templates = ref<TemplateSummary[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 12
const loading = ref(false)
const searchQuery = ref('')
const selectedCategory = ref('')
const previewTemplate = ref<TemplateSummary | null>(null)
const previewDetail = ref<TemplateDetail | null>(null)
const cloning = ref(false)

const categories = [
  { value: '', label: 'All' },
  { value: 'general', label: 'General' },
  { value: 'qa', label: 'Q&A' },
  { value: 'search', label: 'Search' },
  { value: 'summarization', label: 'Summarization' },
  { value: 'analysis', label: 'Analysis' },
  { value: 'customer_support', label: 'Customer Support' },
]

async function fetchTemplates() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: page.value,
      page_size: pageSize,
    }
    if (selectedCategory.value) {
      params.category = selectedCategory.value
    }
    if (searchQuery.value.trim()) {
      params.search = searchQuery.value.trim()
    }

    const response = await apiClient.get('/v1/templates', { params })
    templates.value = response.data.items
    total.value = response.data.total
  } catch (err) {
    console.error('Failed to fetch templates:', err)
    templates.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function openPreview(template: TemplateSummary) {
  previewTemplate.value = template
  previewDetail.value = null

  try {
    const response = await apiClient.get(`/v1/templates/${template.id}`)
    previewDetail.value = response.data
  } catch (err) {
    console.error('Failed to fetch template details:', err)
  }
}

async function useTemplate() {
  if (!previewTemplate.value) return

  cloning.value = true
  try {
    const name = `${previewTemplate.value.name} (Copy)`
    const response = await apiClient.post(
      `/v1/templates/${previewTemplate.value.id}/clone`,
      null,
      { params: { new_name: name } }
    )

    const newConfigId = response.data.id
    previewTemplate.value = null

    // Redirect to wizard with the cloned config
    router.push(`/wizard/${newConfigId}`)
  } catch (err) {
    console.error('Failed to clone template:', err)
  } finally {
    cloning.value = false
  }
}

function changePage(newPage: number) {
  page.value = newPage
}

// Watch for filter changes
let searchTimeout: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    page.value = 1
    fetchTemplates()
  }, 300)
})

watch(selectedCategory, () => {
  page.value = 1
  fetchTemplates()
})

watch(page, () => {
  fetchTemplates()
})

onMounted(() => {
  fetchTemplates()
})
</script>
