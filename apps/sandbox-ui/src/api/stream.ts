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
  const url = new URL(`${apiBase}/v1/stream/`, window.location.origin)
  url.searchParams.set('query', query)
  url.searchParams.set('config_id', configId)
  url.searchParams.set('token', token)

  const controller = new AbortController()

  // Use fetch + ReadableStream instead of EventSource.
  // EventSource doesn't work reliably through Vite's dev proxy
  // because http-proxy buffers the SSE response.
  fetch(url.toString(), {
    signal: controller.signal,
    headers: { 'Accept': 'text/event-stream' },
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Stream request failed: ${response.status}`)
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // SSE format: each event is "data: <json>\n\n"
        // Strip \r to handle \r\n line endings from sse-starlette
        buffer = buffer.replace(/\r/g, '')
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data: ')) continue

          try {
            const data: StreamEvent = JSON.parse(line.slice(6))

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
                return
              case 'error':
                onError(new Error(typeof data.content === 'string' ? data.content : 'Stream error'))
                return
            }
          } catch {
            // Skip malformed events
          }
        }
      }

      // Stream ended without explicit done event
      onDone()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onError(err instanceof Error ? err : new Error('Stream connection error'))
      }
    })

  return () => {
    controller.abort()
  }
}
