import apiClient from './client'
import type { RAGConfig, RAGConfigSummary, PaginatedResponse } from '@/types'

export const configApi = {
  async list(page = 1, pageSize = 100): Promise<PaginatedResponse<RAGConfigSummary>> {
    const response = await apiClient.get('/v1/configs', {
      params: { page, page_size: pageSize },
    })
    return response.data
  },

  async get(id: string): Promise<RAGConfig> {
    const response = await apiClient.get(`/v1/configs/${id}`)
    return response.data
  },
}
