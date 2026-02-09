<template>
  <div class="flex gap-4">
    <!-- Avatar -->
    <div class="flex-shrink-0">
      <div class="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
        <SparklesIcon class="w-5 h-5 text-gray-600" />
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 max-w-3xl">
      <!-- Header -->
      <div class="flex items-center gap-2 mb-1">
        <span class="text-sm font-medium text-gray-900">Assistant</span>
        <span class="text-xs text-gray-400">{{ formatTime(new Date()) }}</span>
        <span class="text-xs text-gray-400">•</span>
        <span class="inline-flex items-center gap-1 text-xs text-gray-500">
          <span class="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
          Thinking...
        </span>
      </div>

      <!-- Bubble with Streaming Content -->
      <div class="inline-block px-4 py-3 bg-white border border-gray-200 rounded-2xl shadow-sm text-gray-900">
        <div v-if="content" class="prose prose-sm max-w-none">
          <MarkdownRenderer :content="content" :is-streaming="true" />
        </div>
        <div v-else class="flex items-center gap-2 text-gray-400">
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></span>
          <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
        </div>
        
        <!-- Blinking Cursor -->
        <span v-if="content" class="inline-block w-2 h-5 bg-primary-500 ml-1 align-middle animate-pulse"></span>
      </div>

      <!-- Sources (if any found so far) -->
      <div v-if="sources.length > 0" class="mt-3">
        <button
          @click="showSourcesPanel = !showSourcesPanel"
          class="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
        >
          <DocumentTextIcon class="w-4 h-4" />
          <span>{{ sources.length }} source{{ sources.length === 1 ? '' : 's' }} found</span>
          <ChevronDownIcon
            class="w-3 h-3 transition-transform"
            :class="showSourcesPanel ? 'rotate-180' : ''"
          />
        </button>

        <!-- Sources Panel -->
        <div v-if="showSourcesPanel" class="mt-2 space-y-2">
          <div
            v-for="source in sources"
            :key="source.id"
            class="p-3 bg-gray-50 rounded-lg border border-gray-200"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="flex items-center gap-1.5 text-xs text-gray-500">
                <FolderIcon class="w-3.5 h-3.5" />
                <span class="truncate">{{ source.metadata.folder_path }}</span>
                <span>/</span>
                <DocumentIcon class="w-3.5 h-3.5" />
                <span class="font-medium text-gray-700">{{ source.metadata.file_name }}</span>
              </div>
              <span
                class="px-1.5 py-0.5 rounded text-xs"
                :class="getSourceTypeClass(source.source_type)"
              >
                {{ source.source_type }}
              </span>
            </div>
            <p class="mt-2 text-sm text-gray-700 line-clamp-2">{{ source.content }}</p>
          </div>
        </div>
      </div>

      <!-- Steps (thinking process) -->
      <div v-if="hasSteps" class="mt-3">
        <div class="inline-flex items-center gap-1.5 text-xs text-gray-500">
          <Cog6ToothIcon class="w-4 h-4 animate-spin" />
          <span>Processing...</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  SparklesIcon,
  DocumentTextIcon,
  ChevronDownIcon,
  FolderIcon,
  DocumentIcon,
  Cog6ToothIcon,
} from '@heroicons/vue/24/outline'
import type { Source } from '@/types'
import MarkdownRenderer from './MarkdownRenderer.vue'

interface Props {
  content: string
  sources: Source[]
}

const props = defineProps<Props>()

const showSourcesPanel = ref(false)

const hasSteps = computed(() => {
  // This could be enhanced to show actual steps from the store
  return false
})

function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

function getSourceTypeClass(type: string): string {
  const classes: Record<string, string> = {
    vector: 'bg-blue-100 text-blue-700',
    keyword: 'bg-green-100 text-green-700',
    graph: 'bg-purple-100 text-purple-700',
  }
  return classes[type] || 'bg-gray-100 text-gray-700'
}
</script>
