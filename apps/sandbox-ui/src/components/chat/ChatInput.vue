<template>
  <div class="relative max-w-4xl mx-auto">
    <div class="relative">
      <textarea
        ref="textareaRef"
        v-model="inputText"
        :disabled="disabled"
        :placeholder="placeholder"
        rows="1"
        class="w-full px-4 py-3 pr-24 bg-white border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-100 disabled:text-gray-500"
        @keydown="handleKeydown"
        @input="autoResize"
      />
      
      <!-- Action Buttons -->
      <div class="absolute right-2 bottom-2 flex items-center gap-2">
        <!-- Character Count -->
        <span
          v-if="showCharCount"
          class="text-xs text-gray-400"
          :class="{ 'text-red-500': isOverLimit }"
        >
          {{ charCount }}/{{ maxLength }}
        </span>

        <!-- Stop Button (shown during streaming) -->
        <button
          v-if="isStreaming"
          @click="handleStop"
          class="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          title="Stop generating"
        >
          <StopIcon class="w-5 h-5" />
        </button>

        <!-- Send Button -->
        <button
          v-else
          @click="handleSend"
          :disabled="!canSend"
          class="p-2 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          :class="canSend ? 'bg-primary-600 hover:bg-primary-700' : 'bg-gray-400'"
          title="Send message"
        >
          <PaperAirplaneIcon class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- Hint -->
    <div class="mt-2 text-xs text-gray-400 flex items-center justify-between">
      <span>Press <kbd class="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600 font-sans">Enter</kbd> to send, <kbd class="px-1.5 py-0.5 bg-gray-100 rounded text-gray-600 font-sans">Shift+Enter</kbd> for new line</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { PaperAirplaneIcon, StopIcon } from '@heroicons/vue/24/solid'
import { useChatStore } from '@/stores/chat'

interface Props {
  disabled?: boolean
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  placeholder: 'Type your message...',
})

const emit = defineEmits<{
  send: [content: string]
  stop: []
}>()

const chatStore = useChatStore()
const textareaRef = ref<HTMLTextAreaElement>()
const inputText = ref('')
const maxLength = 4000
const showCharCount = computed(() => inputText.value.length > 1000)

const charCount = computed(() => inputText.value.length)
const isOverLimit = computed(() => charCount.value > maxLength)
const isStreaming = computed(() => chatStore.isStreaming)
const canSend = computed(() => {
  return inputText.value.trim().length > 0 && !isOverLimit.value && !props.disabled
})

function autoResize() {
  nextTick(() => {
    const textarea = textareaRef.value
    if (!textarea) return

    textarea.style.height = 'auto'
    const newHeight = Math.min(textarea.scrollHeight, 200)
    textarea.style.height = `${newHeight}px`
  })
}

function handleSend() {
  if (!canSend.value) return

  const content = inputText.value.trim()
  if (content) {
    emit('send', content)
    inputText.value = ''
    nextTick(() => {
      const textarea = textareaRef.value
      if (textarea) {
        textarea.style.height = 'auto'
      }
    })
  }
}

function handleStop() {
  emit('stop')
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

// Reset height when text is cleared
watch(inputText, (newValue) => {
  if (!newValue) {
    nextTick(() => {
      const textarea = textareaRef.value
      if (textarea) {
        textarea.style.height = 'auto'
      }
    })
  }
})
</script>

<style scoped>
kbd {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
</style>
