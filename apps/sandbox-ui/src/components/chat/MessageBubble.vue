<template>
  <div class="flex gap-4" :class="message.role === 'user' ? 'flex-row-reverse' : ''">
    <!-- Avatar -->
    <div class="flex-shrink-0">
      <div
        class="w-8 h-8 rounded-full flex items-center justify-center"
        :class="message.role === 'user' ? 'bg-primary-600' : 'bg-gray-200'"
      >
        <UserIcon v-if="message.role === 'user'" class="w-5 h-5 text-white" />
        <SparklesIcon v-else class="w-5 h-5 text-gray-600" />
      </div>
    </div>

    <!-- Message Content -->
    <div class="flex-1 max-w-3xl" :class="message.role === 'user' ? 'text-right' : ''">
      <!-- Header -->
      <div class="flex items-center gap-2 mb-1" :class="message.role === 'user' ? 'justify-end' : ''">
        <span class="text-sm font-medium text-gray-900">
          {{ message.role === 'user' ? 'You' : 'Assistant' }}
        </span>
        <span class="text-xs text-gray-400">
          {{ formatTime(message.timestamp) }}
        </span>
      </div>

      <!-- Bubble -->
      <div
        class="inline-block text-left px-4 py-3 rounded-2xl"
        :class="message.role === 'user'
          ? 'bg-primary-600 text-white'
          : 'bg-white border border-gray-200 text-gray-900 shadow-sm'
        "
      >
        <MarkdownRenderer :content="message.content" :is-user="message.role === 'user'" />
      </div>

      <!-- Sources -->
      <div v-if="showSources" class="mt-3">
        <button
          @click="showSourcesPanel = !showSourcesPanel"
          class="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 transition-colors"
        >
          <DocumentTextIcon class="w-4 h-4" />
          <span>{{ message.sources?.length }} source{{ message.sources?.length === 1 ? '' : 's' }}</span>
          <ChevronDownIcon
            class="w-3 h-3 transition-transform"
            :class="showSourcesPanel ? 'rotate-180' : ''"
          />
        </button>

        <!-- Sources Panel -->
        <div
          v-if="showSourcesPanel"
          class="mt-2 space-y-2"
        >
          <div
            v-for="source in message.sources"
            :key="source.id"
            class="p-3 bg-gray-50 rounded-lg border border-gray-200 text-left"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="flex items-center gap-1.5 text-xs text-gray-500">
                <FolderIcon class="w-3.5 h-3.5" />
                <span class="truncate">{{ source.metadata.folder_path }}</span>
                <span>/</span>
                <DocumentIcon class="w-3.5 h-3.5" />
                <span class="font-medium text-gray-700">{{ source.metadata.file_name }}</span>
              </div>
              <div class="flex items-center gap-1 text-xs">
                <span
                  class="px-1.5 py-0.5 rounded"
                  :class="getSourceTypeClass(source.source_type)"
                >
                  {{ source.source_type }}
                </span>
                <span class="text-gray-400">{{ (source.score * 100).toFixed(1) }}%</span>
              </div>
            </div>
            <p class="mt-2 text-sm text-gray-700 line-clamp-2">{{ source.content }}</p>
            <div class="mt-1.5 text-xs text-gray-400">
              Chunk {{ source.metadata.chunk_index + 1 }}
              <span v-if="source.metadata.page">• Page {{ source.metadata.page }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div
        v-if="message.role === 'assistant'"
        class="flex items-center gap-2 mt-2"
      >
        <button
          @click="copyToClipboard"
          class="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
          title="Copy to clipboard"
        >
          <ClipboardDocumentIcon v-if="!copied" class="w-4 h-4" />
          <CheckIcon v-else class="w-4 h-4 text-green-500" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  UserIcon,
  SparklesIcon,
  DocumentTextIcon,
  ChevronDownIcon,
  FolderIcon,
  DocumentIcon,
  ClipboardDocumentIcon,
  CheckIcon,
} from '@heroicons/vue/24/outline'
import type { Message } from '@/types'
import MarkdownRenderer from './MarkdownRenderer.vue'

interface Props {
  message: Message
  showSources?: boolean
}

const props = defineProps<Props>()

const copied = ref(false)
const showSourcesPanel = ref(false)

function formatTime(timestamp: Date): string {
  return new Date(timestamp).toLocaleTimeString('en-US', {
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

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}
</script>
