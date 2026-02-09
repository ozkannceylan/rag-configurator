<template>
  <div class="space-y-6">
    <h3 class="text-lg font-medium text-gray-900">Review Configuration</h3>
    <p class="text-sm text-gray-600">
      Review your RAG pipeline configuration before saving. You can go back to any step to make changes.
    </p>

    <!-- Validation Status -->
    <div v-if="!isValid" class="bg-red-50 border border-red-200 rounded-lg p-4">
      <h4 class="text-sm font-medium text-red-800 mb-2">⚠️ Configuration Incomplete</h4>
      <ul class="text-sm text-red-600 list-disc list-inside space-y-1">
        <li v-for="error in validationErrors" :key="error">{{ error }}</li>
      </ul>
    </div>

    <div v-else class="bg-green-50 border border-green-200 rounded-lg p-4">
      <p class="text-sm text-green-800">✓ Configuration is valid and ready to save</p>
    </div>

    <!-- Configuration Summary -->
    <div class="bg-white border border-gray-200 rounded-lg divide-y">
      <!-- Basic Info -->
      <div class="p-4">
        <div class="flex items-center justify-between mb-2">
          <h4 class="font-medium text-gray-900">Basic Information</h4>
          <button
            @click="goToStep(0)"
            class="text-xs text-primary-600 hover:text-primary-700"
          >
            Edit
          </button>
        </div>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div class="text-gray-500">Name:</div>
          <div class="text-gray-900 font-medium">{{ config.name || 'Not set' }}</div>
          <div class="text-gray-500">Description:</div>
          <div class="text-gray-900">{{ config.description || 'None' }}</div>
        </div>
      </div>

      <!-- Data Source -->
      <div class="p-4">
        <div class="flex items-center justify-between mb-2">
          <h4 class="font-medium text-gray-900">Data Source</h4>
          <button
            @click="goToStep(0)"
            class="text-xs text-primary-600 hover:text-primary-700"
          >
            Edit
          </button>
        </div>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div class="text-gray-500">Type:</div>
          <div class="text-gray-900">{{ config.data_source?.type || 'local' }}</div>
          <div class="text-gray-500">Folders:</div>
          <div class="text-gray-900">{{ config.data_source?.folders?.length || 0 }} selected</div>
          <div class="text-gray-500">File Patterns:</div>
          <div class="text-gray-900">{{ config.data_source?.folders?.[0]?.file_patterns?.join(', ') || '*' }}</div>
          <div class="text-gray-500">Recursive:</div>
          <div class="text-gray-900">{{ config.data_source?.folders?.[0]?.recursive !== false ? 'Yes' : 'No' }}</div>
        </div>
      </div>

      <!-- RBAC -->
      <div class="p-4">
        <div class="flex items-center justify-between mb-2">
          <h4 class="font-medium text-gray-900">Access Control</h4>
          <button
            @click="goToStep(1)"
            class="text-xs text-primary-600 hover:text-primary-700"
          >
            Edit
          </button>
        </div>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div class="text-gray-500">Enabled:</div>
          <div class="text-gray-900">{{ config.rbac?.enabled ? 'Yes' : 'No' }}</div>
          <div v-if="config.rbac?.enabled" class="text-gray-500">Roles:</div>
          <div v-if="config.rbac?.enabled" class="text-gray-900">{{ config.rbac?.roles?.map(r => r.name).join(', ') }}</div>
        </div>
      </div>

      <!-- Models -->
      <div class="p-4">
        <div class="flex items-center justify-between mb-2">
          <h4 class="font-medium text-gray-900">Models</h4>
          <button
            @click="goToStep(2)"
            class="text-xs text-primary-600 hover:text-primary-700"
          >
            Edit
          </button>
        </div>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div class="text-gray-500">LLM Provider:</div>
          <div class="text-gray-900">{{ config.models?.llm?.provider }}</div>
          <div class="text-gray-500">LLM Model:</div>
          <div class="text-gray-900">{{ config.models?.llm?.model_name }}</div>
          <div class="text-gray-500">Embedding Provider:</div>
          <div class="text-gray-900">{{ config.models?.embedding?.provider }}</div>
          <div class="text-gray-500">Embedding Model:</div>
          <div class="text-gray-900">{{ config.models?.embedding?.model_name }}</div>
        </div>
      </div>

      <!-- Retrieval -->
      <div class="p-4">
        <div class="flex items-center justify-between mb-2">
          <h4 class="font-medium text-gray-900">Retrieval</h4>
          <button
            @click="goToStep(3)"
            class="text-xs text-primary-600 hover:text-primary-700"
          >
            Edit
          </button>
        </div>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div class="text-gray-500">Method:</div>
          <div class="text-gray-900">{{ config.retrieval?.method }}</div>
          <div class="text-gray-500">Chunking:</div>
          <div class="text-gray-900">{{ config.chunking?.strategy }}</div>
          <div class="text-gray-500">Chunk Size:</div>
          <div class="text-gray-900">{{ config.chunking?.chunk_size }}</div>
          <div class="text-gray-500">Top K:</div>
          <div class="text-gray-900">{{ config.retrieval?.vector?.top_k }}</div>
        </div>
      </div>

      <!-- Graph -->
      <div v-if="config.retrieval?.graph?.enabled" class="p-4">
        <div class="flex items-center justify-between mb-2">
          <h4 class="font-medium text-gray-900">Knowledge Graph</h4>
          <button
            @click="goToStep(4)"
            class="text-xs text-primary-600 hover:text-primary-700"
          >
            Edit
          </button>
        </div>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div class="text-gray-500">Enabled:</div>
          <div class="text-gray-900">Yes</div>
          <div class="text-gray-500">Max Depth:</div>
          <div class="text-gray-900">{{ config.retrieval?.graph?.max_depth }}</div>
          <div class="text-gray-500">Node Types:</div>
          <div class="text-gray-900">{{ config.retrieval?.graph?.schema?.nodes?.length || 0 }}</div>
          <div class="text-gray-500">Relation Types:</div>
          <div class="text-gray-900">{{ config.retrieval?.graph?.schema?.relations?.length || 0 }}</div>
        </div>
      </div>

      <!-- Agent -->
      <div class="p-4">
        <div class="flex items-center justify-between mb-2">
          <h4 class="font-medium text-gray-900">Agent</h4>
          <button
            @click="goToStep(5)"
            class="text-xs text-primary-600 hover:text-primary-700"
          >
            Edit
          </button>
        </div>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div class="text-gray-500">Template:</div>
          <div class="text-gray-900">{{ config.agent?.template }}</div>
          <div class="text-gray-500">Max Iterations:</div>
          <div class="text-gray-900">{{ config.agent?.max_iterations }}</div>
          <div class="text-gray-500">LLM Judge:</div>
          <div class="text-gray-900">{{ config.agent?.enable_judge ? 'Enabled' : 'Disabled' }}</div>
        </div>
      </div>

      <!-- Prompts -->
      <div class="p-4">
        <div class="flex items-center justify-between mb-2">
          <h4 class="font-medium text-gray-900">Prompts</h4>
          <button
            @click="goToStep(6)"
            class="text-xs text-primary-600 hover:text-primary-700"
          >
            Edit
          </button>
        </div>
        <div class="space-y-2">
          <div>
            <div class="text-xs text-gray-500 mb-1">System Prompt:</div>
            <div class="text-sm text-gray-900 bg-gray-50 p-2 rounded max-h-24 overflow-y-auto">
              {{ config.prompts?.system_prompt }}
            </div>
          </div>
          <div>
            <div class="text-xs text-gray-500 mb-1">RAG Template:</div>
            <div class="text-sm text-gray-900 bg-gray-50 p-2 rounded max-h-24 overflow-y-auto">
              {{ config.prompts?.rag_prompt_template }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Estimated Resources -->
    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <h4 class="font-medium text-blue-900 mb-2">📊 Estimated Resources</h4>
      <div class="grid grid-cols-3 gap-4 text-sm">
        <div>
          <div class="text-blue-700 font-medium">Processing</div>
          <div class="text-blue-600">{{ estimatedChunks }} chunks</div>
        </div>
        <div>
          <div class="text-blue-700 font-medium">Storage</div>
          <div class="text-blue-600">~{{ estimatedStorage }} MB</div>
        </div>
        <div>
          <div class="text-blue-700 font-medium">Query Cost</div>
          <div class="text-blue-600">~{{ estimatedQueryCost }} tokens/query</div>
        </div>
      </div>
      <p class="text-xs text-blue-600 mt-2">
        Estimates based on configuration. Actual values depend on document sizes and content.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWizardStore } from '@/stores/wizard'

const wizardStore = useWizardStore()
const config = wizardStore.config

const validationErrors = computed(() => {
  const errors: string[] = []
  
  if (!config.name?.trim()) {
    errors.push('Configuration name is required')
  }
  
  if (!config.data_source?.folders?.length) {
    errors.push('At least one folder must be selected')
  }
  

  if (!config.models?.llm?.model_name) {
    errors.push('LLM model must be selected')
  }
  
  if (!config.models?.embedding?.model_name) {
    errors.push('Embedding model must be selected')
  }
  
  if (!config.prompts?.rag_prompt_template?.includes('{context}') ||
      !config.prompts?.rag_prompt_template?.includes('{query}')) {
    errors.push('RAG template must include {context} and {query} placeholders')
  }
  
  return errors
})

const isValid = computed(() => validationErrors.value.length === 0)

const estimatedChunks = computed(() => {
  const folders = config.data_source?.folders?.length || 1
  const avgFilesPerFolder = 10
  const chunksPerFile = Math.ceil(1000 / (config.chunking?.chunk_size || 512))
  return folders * avgFilesPerFolder * chunksPerFile
})

const estimatedStorage = computed(() => {
  const chunks = estimatedChunks.value
  const dims = config.models?.embedding?.dimensions || 1536
  const bytesPerDim = 4 // float32
  const embeddingSize = (chunks * dims * bytesPerDim) / (1024 * 1024)
  const textSize = chunks * (config.chunking?.chunk_size || 512) * 2 / (1024 * 1024)
  return Math.round((embeddingSize + textSize) * 10) / 10
})

const estimatedQueryCost = computed(() => {
  const topK = config.retrieval?.vector?.top_k || 5
  const chunkSize = config.chunking?.chunk_size || 512
  const contextTokens = topK * chunkSize
  const systemPromptTokens = (config.prompts?.system_prompt?.length || 200) / 4
  const ragTemplateTokens = (config.prompts?.rag_prompt_template?.length || 100) / 4
  const queryTokens = 50 // estimate
  const answerTokens = config.models?.llm?.max_tokens || 2048
  
  return Math.round(contextTokens + systemPromptTokens + ragTemplateTokens + queryTokens + answerTokens)
})

function goToStep(step: number) {
  wizardStore.goToStep(step)
}
</script>
