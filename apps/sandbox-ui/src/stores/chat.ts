import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Message, Source, DebugStep } from '@/types'
import { createStreamConnection } from '@/api/stream'
import { useAuthStore } from './auth'
import { useConfigStore } from './config'

export const useChatStore = defineStore('chat', () => {
  // State
  const messages = ref<Message[]>([])
  const isStreaming = ref(false)
  const currentSources = ref<Source[]>([])
  const currentSteps = ref<DebugStep[]>([])
  const streamingContent = ref('')
  const error = ref<string | null>(null)
  let cleanupStream: (() => void) | null = null

  // Getters
  const hasMessages = computed(() => messages.value.length > 0)
  const lastMessage = computed(() => messages.value[messages.value.length - 1])

  // Actions
  async function sendMessage(content: string) {
    const authStore = useAuthStore()
    const configStore = useConfigStore()

    if (!configStore.selectedConfig) {
      error.value = 'No configuration selected'
      return
    }

    if (!authStore.accessToken) {
      error.value = 'Not authenticated'
      return
    }

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    messages.value.push(userMessage)

    // Reset for streaming
    isStreaming.value = true
    streamingContent.value = ''
    currentSources.value = []
    currentSteps.value = []
    error.value = null

    // Create streaming message placeholder
    const streamMessageId = (Date.now() + 1).toString()

    // Start stream
    cleanupStream = createStreamConnection(
      content,
      configStore.selectedConfig.id!,
      authStore.accessToken,
      (token) => {
        streamingContent.value += token
      },
      (source) => {
        currentSources.value.push(source)
      },
      (step) => {
        currentSteps.value.push(step)
      },
      () => {
        // Stream complete
        isStreaming.value = false
        const assistantMessage: Message = {
          id: streamMessageId,
          role: 'assistant',
          content: streamingContent.value,
          timestamp: new Date(),
          sources: [...currentSources.value],
        }
        messages.value.push(assistantMessage)
        cleanupStream = null
      },
      (err) => {
        error.value = err.message
        isStreaming.value = false
        cleanupStream = null
      }
    )
  }

  function clearChat() {
    if (cleanupStream) {
      cleanupStream()
      cleanupStream = null
    }
    messages.value = []
    isStreaming.value = false
    streamingContent.value = ''
    currentSources.value = []
    currentSteps.value = []
    error.value = null
  }

  function stopStreaming() {
    if (cleanupStream) {
      cleanupStream()
      cleanupStream = null
    }
    isStreaming.value = false
    
    // Save partial response if any
    if (streamingContent.value) {
      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: streamingContent.value + '\n\n[Stopped]',
        timestamp: new Date(),
        sources: [...currentSources.value],
      }
      messages.value.push(assistantMessage)
    }
  }

  return {
    messages,
    isStreaming,
    streamingContent,
    currentSources,
    currentSteps,
    error,
    hasMessages,
    lastMessage,
    sendMessage,
    clearChat,
    stopStreaming,
  }
})
