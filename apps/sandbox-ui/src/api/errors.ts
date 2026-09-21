import axios from 'axios'

/**
 * Error payload shapes the gateway and the FastAPI services return:
 * the `{success, data, error, meta}` envelope, a bare `{message}` body, or
 * FastAPI's own `{detail}`.
 */
interface ApiErrorBody {
  message?: string
  detail?: string
  error?: { message?: string }
}

function errorBody(err: unknown): ApiErrorBody | undefined {
  if (!axios.isAxiosError(err)) return undefined
  const data = err.response?.data
  return data && typeof data === 'object' ? (data as ApiErrorBody) : undefined
}

/** HTTP status of a failed request, or undefined when no response arrived. */
export function errorStatus(err: unknown): number | undefined {
  return axios.isAxiosError(err) ? err.response?.status : undefined
}

/** True when the request never reached the server. */
export function isNetworkError(err: unknown): boolean {
  return axios.isAxiosError(err) && (err.code === 'ERR_NETWORK' || err.message === 'Network Error')
}

/** The message the server sent, if it sent one. */
export function apiErrorMessage(err: unknown): string | undefined {
  const body = errorBody(err)
  return body?.error?.message || body?.message || body?.detail || undefined
}

/** The server's message, else the thrown error's own message, else `fallback`. */
export function errorMessage(err: unknown, fallback: string): string {
  return apiErrorMessage(err) || (err instanceof Error ? err.message : '') || fallback
}
