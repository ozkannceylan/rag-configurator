<template>
  <div ref="scrollContainerRef" class="h-full overflow-y-auto px-4 py-6 space-y-6">
    <!-- Messages with Date Separators -->
    <template v-for="(message, index) in messages" :key="message.id">
      <!-- Date Separator -->
      <div
        v-if="shouldShowDateSeparator(index)"
        class="flex items-center justify-center"
      >
        <div class="bg-gray-100 text-gray-500 text-xs px-3 py-1 rounded-full">
          {{ formatDate(message.timestamp) }}
        </div>
      </div>

      <!-- Message Bubble -->
      <MessageBubble
        :message="message"
        :show-sources="message.role === 'assistant' && message.sources && message.sources.length > 0"
      />
    </template>

    <!-- Streaming Message -->
    <StreamingMessage
      v-if="isStreaming"
      :content="streamingContent"
      :sources="currentSources"
    />

    <!-- Scroll to Bottom Button -->
    <button
      v-if="showScrollButton"
      @click="scrollToBottom"
      class="fixed bottom-24 right-8 p-2 bg-white shadow-lg rounded-full border border-gray-200 hover:bg-gray-50 transition-colors z-10"
      title="Scroll to bottom"
    >
      <ArrowDownIcon class="w-5 h-5 text-gray-600" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { ArrowDownIcon } from '@heroicons/vue/24/outline'
import type { Message, Source } from '@/types'
import MessageBubble from './MessageBubble.vue'
import StreamingMessage from './StreamingMessage.vue'

interface Props {
  messages: Message[]
  isStreaming: boolean
  streamingContent: string
  currentSources: Source[]
}

const props = defineProps<Props>()

const scrollContainerRef = ref<HTMLDivElement>()
const showScrollButton = ref(false)
let isUserScrolling = false
let scrollTimeout: number | null = null

function shouldShowDateSeparator(index: number): boolean {
  if (index === 0) return true
  
  const current = new Date(props.messages[index].timestamp)
  const previous = new Date(props.messages[index - 1].timestamp)
  
  return !isSameDay(current, previous)
}

function isSameDay(date1: Date, date2: Date): boolean {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  )
}

function formatDate(timestamp: Date): string {
  const date = new Date(timestamp)
  const now = new Date()
  
  if (isSameDay(date, now)) {
    return 'Today'
  }
  
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (isSameDay(date, yesterday)) {
    return 'Yesterday'
  }
  
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}

function scrollToBottom() {
  const container = scrollContainerRef.value
  if (container) {
    container.scrollTop = container.scrollHeight
    showScrollButton.value = false
  }
}

function handleScroll() {
  const container = scrollContainerRef.value
  if (!container) return

  // Detect if user is manually scrolling
  if (scrollTimeout) {
    clearTimeout(scrollTimeout)
  }
  isUserScrolling = true
  scrollTimeout = window.setTimeout(() => {
    isUserScrolling = false
  }, 150)

  // Show scroll button if not at bottom
  const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100
  showScrollButton.value = !isAtBottom
}

// Auto-scroll to bottom when new messages arrive or streaming updates
watch(
  () => [props.messages.length, props.streamingContent],
  () => {
    if (!isUserScrolling) {
      nextTick(() => {
        scrollToBottom()
      })
    }
  },
  { flush: 'post' }
)

onMounted(() => {
  const container = scrollContainerRef.value
  if (container) {
    container.addEventListener('scroll', handleScroll)
    scrollToBottom()
  }
})
</script>
