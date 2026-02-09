<template>
  <div class="space-y-8">
    <!-- LLM Configuration -->
    <div class="space-y-4">
      <h3 class="text-lg font-medium text-gray-900">Language Model (LLM)</h3>
      <p class="text-sm text-gray-600">Configure the main AI model for answering questions</p>

      <!-- Provider Selection -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <button
          v-for="provider in llmProviders"
          :key="provider.id"
          @click="setLLMProvider(provider.id)"
          :class="[
            'p-3 border-2 rounded-lg text-center transition-all',
            config.models.llm.provider === provider.id
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-200 hover:border-gray-300'
          ]"
        >
          <div class="text-2xl mb-1">{{ provider.icon }}</div>
          <div class="text-sm font-medium">{{ provider.name }}</div>
        </button>
      </div>

      <!-- OpenAI Specific -->
      <div v-if="config.models.llm.provider === 'openai'" class="space-y-4 bg-gray-50 p-4 rounded-lg">
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Model</label>
          <select
            v-model="config.models.llm.model_name"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="gpt-4o">GPT-4o</option>
            <option value="gpt-4o-mini">GPT-4o Mini</option>
            <option value="gpt-4-turbo">GPT-4 Turbo</option>
            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
          </select>
        </div>
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">API Key (Optional)</label>
          <input
            v-model="config.models.llm.api_key"
            type="password"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="sk-... (or use environment variable)"
          />
        </div>
      </div>

      <!-- Anthropic Specific -->
      <div v-else-if="config.models.llm.provider === 'anthropic'" class="space-y-4 bg-gray-50 p-4 rounded-lg">
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Model</label>
          <select
            v-model="config.models.llm.model_name"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
            <option value="claude-3-opus-20240229">Claude 3 Opus</option>
            <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
            <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
          </select>
        </div>
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">API Key (Optional)</label>
          <input
            v-model="config.models.llm.api_key"
            type="password"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="sk-ant-... (or use environment variable)"
          />
        </div>
      </div>

      <!-- Ollama Specific -->
      <div v-else-if="config.models.llm.provider === 'ollama'" class="space-y-4 bg-gray-50 p-4 rounded-lg">
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Base URL</label>
          <input
            v-model="config.models.llm.base_url"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="http://localhost:11434"
          />
        </div>
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Model</label>
          <input
            v-model="config.models.llm.model_name"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="llama2, mistral, codellama..."
          />
        </div>
      </div>

      <!-- vLLM Specific -->
      <div v-else-if="config.models.llm.provider === 'vllm'" class="space-y-4 bg-gray-50 p-4 rounded-lg">
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Base URL</label>
          <input
            v-model="config.models.llm.base_url"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="http://localhost:8000/v1"
          />
        </div>
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Model</label>
          <input
            v-model="config.models.llm.model_name"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="model-name"
          />
        </div>
      </div>

      <!-- Temperature and Max Tokens -->
      <div class="grid grid-cols-2 gap-4">
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">
            Temperature: {{ config.models.llm.temperature }}
          </label>
          <input
            v-model.number="config.models.llm.temperature"
            type="range"
            min="0"
            max="2"
            step="0.1"
            class="w-full"
          />
          <p class="text-xs text-gray-500">Lower = more focused, Higher = more creative</p>
        </div>
        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Max Tokens</label>
          <input
            v-model.number="config.models.llm.max_tokens"
            type="number"
            min="256"
            max="8192"
            step="256"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>
    </div>

    <!-- Embedding Model -->
    <div class="space-y-4 pt-6 border-t">
      <h3 class="text-lg font-medium text-gray-900">Embedding Model</h3>
      <p class="text-sm text-gray-600">Configure the model for creating document embeddings</p>

      <!-- Provider Selection -->
      <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
        <button
          v-for="provider in embeddingProviders"
          :key="provider.id"
          @click="setEmbeddingProvider(provider.id)"
          :class="[
            'p-3 border-2 rounded-lg text-center transition-all',
            config.models.embedding.provider === provider.id
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-200 hover:border-gray-300'
          ]"
        >
          <div class="text-2xl mb-1">{{ provider.icon }}</div>
          <div class="text-sm font-medium">{{ provider.name }}</div>
        </button>
      </div>

      <!-- Embedding Model Details -->
      <div class="bg-gray-50 p-4 rounded-lg space-y-4">
        <div v-if="config.models.embedding.provider === 'openai'" class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Model</label>
          <select
            v-model="config.models.embedding.model_name"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="text-embedding-3-small">text-embedding-3-small (1536d)</option>
            <option value="text-embedding-3-large">text-embedding-3-large (3072d)</option>
            <option value="text-embedding-ada-002">text-embedding-ada-002 (1536d)</option>
          </select>
        </div>

        <div v-else-if="config.models.embedding.provider === 'ollama'" class="space-y-4">
          <div class="space-y-2">
            <label class="block text-sm font-medium text-gray-700">Base URL</label>
            <input
              v-model="config.models.embedding.base_url"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              placeholder="http://localhost:11434"
            />
          </div>
          <div class="space-y-2">
            <label class="block text-sm font-medium text-gray-700">Model</label>
            <input
              v-model="config.models.embedding.model_name"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              placeholder="nomic-embed-text, mxbai-embed-large..."
            />
          </div>
        </div>

        <div v-else-if="config.models.embedding.provider === 'huggingface'" class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Model</label>
          <input
            v-model="config.models.embedding.model_name"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="sentence-transformers/all-MiniLM-L6-v2"
          />
          <p class="text-xs text-gray-500">Use HuggingFace model name or local path</p>
        </div>

        <div class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Dimensions</label>
          <input
            v-model.number="config.models.embedding.dimensions"
            type="number"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            placeholder="Auto-detected if empty"
          />
          <p class="text-xs text-gray-500">Optional - will be auto-detected from model</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useWizardStore } from '@/stores/wizard'

const wizardStore = useWizardStore()
const config = wizardStore.config

const llmProviders = [
  { id: 'openai', name: 'OpenAI', icon: '🅾️' },
  { id: 'anthropic', name: 'Anthropic', icon: '🅰️' },
  { id: 'ollama', name: 'Ollama', icon: '🦙' },
  { id: 'vllm', name: 'vLLM', icon: '⚡' },
]

const embeddingProviders = [
  { id: 'openai', name: 'OpenAI', icon: '🅾️' },
  { id: 'ollama', name: 'Ollama', icon: '🦙' },
  { id: 'huggingface', name: 'HuggingFace', icon: '🤗' },
]

const defaultLLMModels: Record<string, string> = {
  openai: 'gpt-4o-mini',
  anthropic: 'claude-3-5-sonnet-20241022',
  ollama: 'llama2',
  vllm: 'default',
}

const defaultEmbeddingModels: Record<string, string> = {
  openai: 'text-embedding-3-small',
  ollama: 'nomic-embed-text',
  huggingface: 'sentence-transformers/all-MiniLM-L6-v2',
}

function setLLMProvider(provider: string) {
  config.models.llm.provider = provider as any
  config.models.llm.model_name = defaultLLMModels[provider]
  
  // Set provider-specific defaults
  if (provider === 'ollama') {
    config.models.llm.base_url = 'http://localhost:11434'
  } else if (provider === 'vllm') {
    config.models.llm.base_url = 'http://localhost:8000/v1'
  } else {
    config.models.llm.base_url = undefined
  }
}

function setEmbeddingProvider(provider: string) {
  config.models.embedding.provider = provider as any
  config.models.embedding.model_name = defaultEmbeddingModels[provider]
  
  // Set provider-specific defaults
  if (provider === 'ollama') {
    config.models.embedding.base_url = 'http://localhost:11434'
  } else if (provider === 'huggingface') {
    config.models.embedding.dimensions = 384
  } else {
    config.models.embedding.base_url = undefined
  }
}
</script>
