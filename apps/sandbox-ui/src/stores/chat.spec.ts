import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useChatStore } from './chat'
import type { Source } from '@/types'

const source: Source = {
  id: 's1',
  content: 'chunk text',
  score: 0.91,
  metadata: { file_name: 'handbook.pdf', folder_path: '/docs', chunk_index: 2 },
  source_type: 'vector',
}

describe('chat store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts with an empty conversation', () => {
    const chat = useChatStore()

    expect(chat.messages).toEqual([])
    expect(chat.hasMessages).toBe(false)
    expect(chat.isStreaming).toBe(false)
    expect(chat.error).toBeNull()
  })

  it('keeps the partial answer when streaming is stopped', () => {
    const chat = useChatStore()

    chat.isStreaming = true
    chat.streamingContent = 'half an answer'
    chat.currentSources = [source]
    chat.stopStreaming()

    expect(chat.isStreaming).toBe(false)
    expect(chat.messages).toHaveLength(1)
    expect(chat.hasMessages).toBe(true)

    const saved = chat.lastMessage
    expect(saved.role).toBe('assistant')
    expect(saved.content).toBe('half an answer\n\n[Stopped]')
    expect(saved.sources).toEqual([source])
  })

  it('does not record an empty message when nothing was streamed', () => {
    const chat = useChatStore()

    chat.isStreaming = true
    chat.stopStreaming()

    expect(chat.isStreaming).toBe(false)
    expect(chat.messages).toEqual([])
  })

  it('clears the conversation and the in-flight stream state', () => {
    const chat = useChatStore()

    chat.isStreaming = true
    chat.streamingContent = 'half an answer'
    chat.currentSources = [source]
    chat.error = 'boom'
    chat.stopStreaming()
    chat.clearChat()

    expect(chat.messages).toEqual([])
    expect(chat.hasMessages).toBe(false)
    expect(chat.isStreaming).toBe(false)
    expect(chat.streamingContent).toBe('')
    expect(chat.currentSources).toEqual([])
    expect(chat.currentSteps).toEqual([])
    expect(chat.error).toBeNull()
  })
})
