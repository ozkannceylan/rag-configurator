<template>
  <div class="flex flex-col h-full bg-gray-50">
    <!-- Messages Area -->
    <div class="flex-1 overflow-hidden">
      <MessageList
        v-if="hasMessages"
        :messages="messages"
        :is-streaming="isStreaming"
        :streaming-content="streamingContent"
        :current-sources="currentSources"
      />
      
      <!-- Empty State -->
      <div
        v-else
        class="h-full flex flex-col items-center justify-center px-4"
      >
        <div class="text-center space-y-4">
          <div class="w-16 h-16 mx-auto bg-primary-100 rounded-full flex items-center justify-center">
            <ChatBubbleLeftRightIcon class="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <h3 class="text-lg font-medium text-gray-900">Start a conversation</h3>
            <p class="text-sm text-gray-500 mt-1 max-w-sm">
              Ask a question about your documents. The AI will search through your configured data sources to find relevant answers.
            </p>
          </div>
          <div class="flex flex-wrap gap-2 justify-center">
            <button
              v-for="suggestion in suggestions"
              :key="suggestion"
              @click="sendSuggestion(suggestion)"
              class="px-3 py-1.5 text-sm bg-white border border-gray-200 rounded-full hover:border-primary-300 hover:bg-primary-50 transition-colors text-gray-600"
            >
              {{ suggestion }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="border-t border-gray-200 bg-white p-4">
      <ChatInput
        :disabled="isStreaming"
        :placeholder="inputPlaceholder"
        @send="handleSend"
        @stop="handleStop"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChatBubbleLeftRightIcon } from '@heroicons/vue/24/outline'
import { useChatStore } from '@/stores/chat'
import { useConfigStore } from '@/stores/config'
import MessageList from './MessageList.vue'
import ChatInput from './ChatInput.vue'

const chatStore = useChatStore()
const configStore = useConfigStore()

const messages = computed(() => chatStore.messages)
const hasMessages = computed(() => chatStore.hasMessages)
const isStreaming = computed(() => chatStore.isStreaming)
const streamingContent = computed(() => chatStore.streamingContent)
const currentSources = computed(() => chatStore.currentSources)

const inputPlaceholder = computed(() => {
  if (!configStore.selectedConfig) {
    return 'Select a configuration first...'
  }
  if (isStreaming.value) {
    return 'AI is thinking...'
  }
  return 'Type your message...'
})

const suggestions = [
  'What are the main topics in my documents?',
  'Summarize the key findings',
  'Find references about...',
  'Explain this concept',
]

function handleSend(content: string) {
  chatStore.sendMessage(content)
}

function handleStop() {
  chatStore.stopStreaming()
}

function sendSuggestion(suggestion: string) {
  chatStore.sendMessage(suggestion)
}
</script>
