import apiClient from './client'
import type { RAGConfig, PaginatedResponse, FolderStructure, IngestionStatus, LogEntry } from '@/types'

export interface BrowseEntry {
  name: string
  path: string
  type: string
  has_children: boolean
}

export interface BrowseResponse {
  current_path: string
  parent_path: string | null
  entries: BrowseEntry[]
}

export const configApi: {
  list(page?: number, pageSize?: number): Promise<PaginatedResponse<RAGConfig>>
  get(id: string): Promise<RAGConfig>
  create(data: Partial<RAGConfig>): Promise<RAGConfig>
  update(id: string, data: Partial<RAGConfig>): Promise<RAGConfig>
  delete(id: string): Promise<void>
  duplicate(id: string): Promise<RAGConfig>
  export(id: string): Promise<Blob>
  import(file: File): Promise<RAGConfig>
  scanFolders(basePath: string): Promise<FolderStructure[]>
  browseFolders(path: string): Promise<BrowseResponse>
} = {
  async list(page = 1, pageSize = 20): Promise<PaginatedResponse<RAGConfig>> {
    const response = await apiClient.get('/v1/configs', {
      params: { page, page_size: pageSize },
    })
    return response.data
  },

  async get(id: string): Promise<RAGConfig> {
    const response = await apiClient.get(`/v1/configs/${id}`)
    return response.data
  },

  async create(data: Partial<RAGConfig>): Promise<RAGConfig> {
    const response = await apiClient.post('/v1/configs', data)
    return response.data
  },

  async update(id: string, data: Partial<RAGConfig>): Promise<RAGConfig> {
    const response = await apiClient.put(`/v1/configs/${id}`, data)
    return response.data
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/v1/configs/${id}`)
  },

  async duplicate(id: string): Promise<RAGConfig> {
    const response = await apiClient.post(`/v1/configs/${id}/duplicate`)
    return response.data
  },

  async export(id: string): Promise<Blob> {
    const response = await apiClient.get(`/v1/configs/${id}/export`, {
      responseType: 'blob',
    })
    return response.data
  },

  async import(file: File): Promise<RAGConfig> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post('/v1/configs/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  async scanFolders(basePath: string): Promise<FolderStructure[]> {
    const response = await apiClient.post('/v1/folders/scan', { base_path: basePath })
    return response.data.folders || response.data || []
  },

  async browseFolders(path: string): Promise<BrowseResponse> {
    const response = await apiClient.post('/v1/folders/browse', { path })
    return response.data
  },
}

export const ingestApi = {
  async start(configId: string): Promise<{ task_id: string }> {
    const response = await apiClient.post(`/v1/ingest/${configId}/start`)
    return response.data
  },

  async status(configId: string): Promise<IngestionStatus> {
    const response = await apiClient.get(`/v1/ingest/${configId}/status`)
    return response.data
  },

  async cancel(configId: string): Promise<void> {
    await apiClient.post(`/v1/ingest/${configId}/cancel`)
  },

  async logs(configId: string): Promise<LogEntry[]> {
    const response = await apiClient.get(`/v1/ingest/${configId}/logs`)
    return response.data
  },
}
