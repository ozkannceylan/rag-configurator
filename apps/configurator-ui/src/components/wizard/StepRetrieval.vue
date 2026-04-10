<template>
  <div class="space-y-8">
    <!-- Chunking Strategy -->
    <div class="space-y-4">
      <h3 class="text-lg font-medium text-gray-900">Chunking Strategy</h3>
      <p class="text-sm text-gray-600">How to split documents into chunks for embedding</p>

      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        <button
          v-for="strategy in chunkingStrategies"
          :key="strategy.id"
          @click="config.chunking.strategy = strategy.id"
          :class="[
            'p-4 border-2 rounded-lg text-left transition-all',
            config.chunking.strategy === strategy.id
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-200 hover:border-gray-300'
          ]"
        >
          <div class="font-medium text-gray-900">{{ strategy.name }}</div>
          <div class="text-xs text-gray-500 mt-1">{{ strategy.description }}</div>
        </button>
      </div>

      <!-- Chunk Settings -->
      <div class="bg-gray-50 p-4 rounded-lg space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <label class="block text-sm font-medium text-gray-700">
              Chunk Size: {{ config.chunking.chunk_size }}
            </label>
            <input
              v-model.number="config.chunking.chunk_size"
              type="range"
              min="128"
              max="2048"
              step="64"
              class="w-full"
            />
            <p class="text-xs text-gray-500">Tokens per chunk</p>
          </div>
          <div class="space-y-2">
            <label class="block text-sm font-medium text-gray-700">
              Chunk Overlap: {{ config.chunking.chunk_overlap }}
            </label>
            <input
              v-model.number="config.chunking.chunk_overlap"
              type="range"
              min="0"
              max="256"
              step="16"
              class="w-full"
            />
            <p class="text-xs text-gray-500">Tokens of overlap between chunks</p>
          </div>
        </div>

        <!-- Separators for recursive chunking -->
        <div v-if="config.chunking.strategy === 'recursive'" class="space-y-2">
          <label class="block text-sm font-medium text-gray-700">Separators</label>
          <div class="flex flex-wrap gap-2">
            <label
              v-for="sep in availableSeparators"
              :key="sep.value"
              class="flex items-center gap-1 px-3 py-1 bg-white border border-gray-300 rounded-full text-sm cursor-pointer hover:bg-gray-50"
            >
              <input
                type="checkbox"
                :checked="isSeparatorSelected(sep.value)"
                @change="toggleSeparator(sep.value)"
                class="w-3 h-3 text-primary-600 rounded focus:ring-primary-500"
              />
              <span>{{ sep.label }}</span>
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Retrieval Method -->
    <div class="space-y-4 pt-6 border-t">
      <h3 class="text-lg font-medium text-gray-900">Retrieval Method</h3>
      <p class="text-sm text-gray-600">How to search for relevant documents</p>

      <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
        <button
          v-for="method in retrievalMethods"
          :key="method.id"
          @click="setRetrievalMethod(method.id)"
          :class="[
            'p-4 border-2 rounded-lg text-left transition-all',
            config.retrieval.method === method.id
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-200 hover:border-gray-300'
          ]"
        >
          <div class="font-medium text-gray-900">{{ method.name }}</div>
          <div class="text-xs text-gray-500 mt-1">{{ method.description }}</div>
        </button>
      </div>

      <!-- Method-specific settings -->
      <div class="bg-gray-50 p-4 rounded-lg space-y-4">
        <!-- Vector Settings -->
        <div v-if="usesVector" class="space-y-4">
          <h4 class="font-medium text-gray-900">Vector Search</h4>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="block text-sm font-medium text-gray-700">
                Top K: {{ config.retrieval.vector.top_k }}
              </label>
              <input
                v-model.number="config.retrieval.vector.top_k"
                type="range"
                min="1"
                max="20"
                step="1"
                class="w-full"
              />
              <p class="text-xs text-gray-500">Number of chunks to retrieve</p>
            </div>
            <div class="space-y-2">
              <label class="block text-sm font-medium text-gray-700">
                Score Threshold: {{ config.retrieval.vector.score_threshold }}
              </label>
              <input
                v-model.number="config.retrieval.vector.score_threshold"
                type="range"
                min="0"
                max="1"
                step="0.05"
                class="w-full"
              />
              <p class="text-xs text-gray-500">Minimum similarity score (0 = any, 1 = exact)</p>
            </div>
          </div>
        </div>

        <!-- Keyword Settings -->
        <div v-if="usesKeyword" class="space-y-4 pt-4 border-t">
          <h4 class="font-medium text-gray-900">Keyword Search</h4>
          <div class="space-y-3">
            <div class="flex items-center gap-3">
              <input
                v-model="config.retrieval.keyword.enabled"
                type="checkbox"
                id="keyword-enabled"
                class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <label for="keyword-enabled" class="text-sm text-gray-700">Enable keyword search</label>
            </div>
            <div class="flex items-center gap-3">
              <input
                v-model="config.retrieval.keyword.use_fuzzy"
                type="checkbox"
                id="fuzzy-match"
                class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <label for="fuzzy-match" class="text-sm text-gray-700">Use fuzzy matching</label>
            </div>
            <div class="space-y-2">
              <label class="block text-sm font-medium text-gray-700">
                Boost Factor: {{ config.retrieval.keyword.boost_factor }}
              </label>
              <input
                v-model.number="config.retrieval.keyword.boost_factor"
                type="range"
                min="0"
                max="2"
                step="0.1"
                class="w-full"
              />
              <p class="text-xs text-gray-500">Weight of keyword results in hybrid search</p>
            </div>
          </div>
        </div>

        <!-- Graph Settings -->
        <div v-if="usesGraph" class="space-y-4 pt-4 border-t">
          <h4 class="font-medium text-gray-900">Knowledge Graph</h4>
          <div class="space-y-3">
            <div class="flex items-center gap-3">
              <input
                v-model="config.retrieval.graph.enabled"
                type="checkbox"
                id="graph-enabled"
                class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <label for="graph-enabled" class="text-sm text-gray-700">Enable knowledge graph</label>
            </div>
            <div class="space-y-2">
              <label class="block text-sm font-medium text-gray-700">
                Max Graph Depth: {{ config.retrieval.graph.max_depth }}
              </label>
              <input
                v-model.number="config.retrieval.graph.max_depth"
                type="range"
                min="1"
                max="5"
                step="1"
                class="w-full"
              />
              <p class="text-xs text-gray-500">How many hops to traverse in the graph</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWizardStore } from '@/stores/wizard'

const wizardStore = useWizardStore()
const config = wizardStore.config

const chunkingStrategies = [
  {
    id: 'recursive',
    name: 'Recursive',
    description: 'Split by separators recursively'
  },
  {
    id: 'semantic',
    name: 'Semantic',
    description: 'Preserve semantic boundaries'
  },
  {
    id: 'document',
    name: 'Document',
    description: 'One chunk per document'
  },
  {
    id: 'late',
    name: 'Late Chunking',
    description: 'Chunk after embedding for better context',
  },
  {
    id: 'raptor',
    name: 'RAPTOR',
    description: 'Recursive abstractive processing for tree-organized retrieval',
  },
]

const retrievalMethods = [
  { 
    id: 'naive', 
    name: 'Vector Only', 
    description: 'Pure semantic similarity' 
  },
  { 
    id: 'keyword', 
    name: 'Keyword Only', 
    description: 'Text-based search' 
  },
  { 
    id: 'hybrid', 
    name: 'Hybrid', 
    description: 'Combine vector + keyword' 
  },
  { 
    id: 'graph', 
    name: 'Graph', 
    description: 'Graph traversal' 
  },
  { 
    id: 'hybrid_graph', 
    name: 'Hybrid + Graph', 
    description: 'All methods combined' 
  },
]

const availableSeparators = [
  { value: '\n\n', label: 'Paragraph' },
  { value: '\n', label: 'Line' },
  { value: '. ', label: 'Sentence' },
  { value: ' ', label: 'Space' },
  { value: '', label: 'Character' },
]

const usesVector = computed(() => {
  return ['naive', 'hybrid', 'hybrid_graph'].includes(config.retrieval.method)
})

const usesKeyword = computed(() => {
  return ['keyword', 'hybrid', 'hybrid_graph'].includes(config.retrieval.method)
})

const usesGraph = computed(() => {
  return ['graph', 'hybrid_graph'].includes(config.retrieval.method)
})

function setRetrievalMethod(method: string) {
  config.retrieval.method = method as any
  
  // Auto-enable graph if graph method selected
  if (['graph', 'hybrid_graph'].includes(method)) {
    config.retrieval.graph.enabled = true
  }
}

function isSeparatorSelected(sep: string): boolean {
  const separators = config.chunking.separators || ['\n\n', '\n', '. ']
  return separators.includes(sep)
}

function toggleSeparator(sep: string) {
  let separators = config.chunking.separators || ['\n\n', '\n', '. ']
  const index = separators.indexOf(sep)
  
  if (index === -1) {
    separators.push(sep)
  } else {
    separators.splice(index, 1)
  }
  
  // Ensure we have at least one separator
  if (separators.length === 0) {
    separators = ['\n\n']
  }
  
  config.chunking.separators = separators
}
</script>
