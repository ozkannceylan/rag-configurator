<template>
  <div class="space-y-4">
    <!-- Error State -->
    <div v-if="result.error" class="bg-red-50 border border-red-200 rounded-lg p-4">
      <p class="text-sm font-medium text-red-800">Error</p>
      <p class="text-sm text-red-600 mt-1">{{ result.error }}</p>
    </div>

    <!-- Metrics -->
    <div class="grid grid-cols-3 gap-3">
      <div class="bg-white border border-gray-200 rounded-lg p-3 text-center">
        <p class="text-xs text-gray-500">Response Time</p>
        <p class="text-lg font-semibold text-gray-900">{{ formattedTime }}</p>
      </div>
      <div class="bg-white border border-gray-200 rounded-lg p-3 text-center">
        <p class="text-xs text-gray-500">Sources</p>
        <p class="text-lg font-semibold text-gray-900">{{ result.sources.length }}</p>
      </div>
      <div class="bg-white border border-gray-200 rounded-lg p-3 text-center">
        <p class="text-xs text-gray-500">Tokens</p>
        <p class="text-lg font-semibold text-gray-900">{{ result.tokenCount ?? '--' }}</p>
      </div>
    </div>

    <!-- Response -->
    <div v-if="result.response" class="bg-white border border-gray-200 rounded-lg p-4">
      <p class="text-xs font-medium text-gray-500 mb-2">Response</p>
      <div class="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">{{ result.response }}</div>
    </div>

    <!-- Sources -->
    <div v-if="result.sources.length > 0" class="space-y-2">
      <p class="text-xs font-medium text-gray-500">Sources Used</p>
      <div
        v-for="(source, idx) in result.sources"
        :key="idx"
        class="bg-white border border-gray-200 rounded-lg p-3"
      >
        <div class="flex items-center justify-between mb-1">
          <span class="text-xs font-medium text-gray-700">
            {{ source.metadata?.file_name || `Source ${idx + 1}` }}
          </span>
          <span
            class="text-xs font-medium px-2 py-0.5 rounded-full"
            :class="scoreClass(source.score)"
          >
            {{ (source.score * 100).toFixed(0) }}%
          </span>
        </div>
        <button
          @click="toggleSource(idx)"
          class="text-xs text-primary-600 hover:text-primary-700"
        >
          {{ expandedSources.has(idx) ? 'Hide content' : 'Show content' }}
        </button>
        <div v-if="expandedSources.has(idx)" class="mt-2 text-xs text-gray-600 bg-gray-50 rounded p-2 max-h-32 overflow-y-auto">
          {{ source.content }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface ComparisonResultData {
  response: string
  responseTime: number
  sources: Array<{
    content: string
    score: number
    metadata: { file_name?: string;[key: string]: unknown }
  }>
  tokenCount: number | null
  error?: string
}

const props = defineProps<{
  result: ComparisonResultData
  label: string
}>()

const expandedSources = ref<Set<number>>(new Set())

const formattedTime = computed(() => {
  if (props.result.responseTime < 1000) {
    return `${props.result.responseTime}ms`
  }
  return `${(props.result.responseTime / 1000).toFixed(2)}s`
})

function scoreClass(score: number): string {
  if (score >= 0.7) return 'bg-green-100 text-green-800'
  if (score >= 0.4) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

function toggleSource(idx: number) {
  if (expandedSources.value.has(idx)) {
    expandedSources.value.delete(idx)
  } else {
    expandedSources.value.add(idx)
  }
  // Force reactivity
  expandedSources.value = new Set(expandedSources.value)
}
</script>
