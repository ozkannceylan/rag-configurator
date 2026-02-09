import type { Source, DebugStep, StreamEvent } from '@/types'

export function createStreamConnection(
  query: string,
  configId: string,
  token: string,
  onToken: (token: string) => void,
  onSource: (source: Source) => void,
  onStep: (step: DebugStep) => void,
  onDone: () => void,
  onError: (error: Error) => void
): () => void {
  const apiBase = import.meta.env.VITE_API_URL || '/api'
  const url = new URL(`${apiBase}/v1/stream`, window.location.origin)
  url.searchParams.set('query', query)
  url.searchParams.set('config_id', configId)
  url.searchParams.set('token', token)
  
  const eventSource = new EventSource(url.toString())
  
  eventSource.onmessage = (event) => {
    try {
      const data: StreamEvent = JSON.parse(event.data)
      
      switch (data.type) {
        case 'token':
          if (typeof data.content === 'string') {
            onToken(data.content)
          }
          break
        case 'source':
          if (data.content && typeof data.content === 'object') {
            onSource(data.content as Source)
          }
          break
        case 'step':
          if (data.content && typeof data.content === 'object') {
            onStep(data.content as DebugStep)
          }
          break
        case 'done':
          onDone()
          eventSource.close()
          break
        case 'error':
          onError(new Error(typeof data.content === 'string' ? data.content : 'Stream error'))
          eventSource.close()
          break
      }
    } catch (err) {
      onError(err instanceof Error ? err : new Error('Failed to parse stream event'))
    }
  }
  
  eventSource.onerror = () => {
    onError(new Error('EventSource connection error'))
    eventSource.close()
  }
  
  return () => {
    eventSource.close()
  }
}
