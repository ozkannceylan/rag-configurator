// User types
export interface User {
  id: string
  email: string
  name: string
  created_at: string
}

// Auth types
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
}

// RAG Config types
export type ConfigStatus =
  | 'draft'
  | 'ready'
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'error'
  | 'running'
  | 'cancelled'

export interface RAGConfigSummary {
  id: string
  name: string
  description?: string
  status?: ConfigStatus
  created_at?: string
  updated_at?: string
}

export interface RAGConfig {
  id: string
  name: string
  description?: string
  data_source: DataSourceConfig
  rbac?: RBACConfig
  models: ModelsConfig
  retrieval: RetrievalConfig
  chunking: ChunkingConfig
  agent: AgentConfig
  prompts: PromptsConfig
  created_at?: string
  updated_at?: string
  status?: ConfigStatus
}

export interface DataSourceConfig {
  type: 'local' | 's3'
  base_path?: string
  bucket?: string
  prefix?: string
  region?: string
  selected_folders: string[]
  file_types: string[]
  recursive: boolean
}

export interface RBACConfig {
  enabled: boolean
  roles: string[]
  folder_permissions: Record<string, string[]>
  default_role: string
}

export interface ModelsConfig {
  llm: LLMConfig
  embedding: EmbeddingConfig
}

export interface LLMConfig {
  provider: 'openai' | 'anthropic' | 'ollama' | 'vllm'
  model_name: string
  api_key?: string
  base_url?: string
  temperature: number
  max_tokens: number
}

export interface EmbeddingConfig {
  provider: 'openai' | 'ollama' | 'huggingface' | 'cohere' | 'voyage' | 'jina'
  model_name: string
  dimensions?: number
  base_url?: string
}

export interface RetrievalConfig {
  method: 'naive' | 'keyword' | 'hybrid' | 'graph' | 'hybrid_graph'
  vector: {
    top_k: number
    score_threshold: number
  }
  keyword?: {
    enabled: boolean
    use_fuzzy: boolean
    boost_factor: number
  }
  graph?: {
    enabled: boolean
    max_depth: number
  }
}

export interface ChunkingConfig {
  strategy: 'recursive' | 'semantic' | 'document' | 'late' | 'raptor'
  chunk_size: number
  chunk_overlap: number
  separators?: string[]
}

export interface AgentConfig {
  template: 'naive_rag' | 'react' | 'crag' | 'self_rag' | 'multi_query' | 'plan_solve' | 'adaptive_rag' | 'agentic_rag' | 'graph_rag'
  max_iterations: number
  enable_streaming: boolean
  temperature_override?: number
  config?: Record<string, any>
}

export interface PromptsConfig {
  system_prompt: string
  rag_prompt_template: string
}

// Chat types
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sources?: Source[]
}

export interface Source {
  id: string
  content: string
  score: number
  metadata: {
    file_name: string
    folder_path: string
    chunk_index: number
    page?: number
  }
  source_type: 'vector' | 'keyword' | 'graph'
}

export interface DebugStep {
  id: string
  name: string
  status: 'running' | 'completed' | 'failed'
  duration_ms: number
  input?: any
  output?: any
  metadata?: Record<string, any>
  timestamp: Date
}

// API response types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// Streaming event types
export type StreamEventType = 'token' | 'source' | 'step' | 'done' | 'error'

export interface StreamEvent {
  type: StreamEventType
  content?: string | Source | DebugStep | any
}

// Agent response types
export interface ChatResponse {
  response: string
  sources: Source[]
  metadata?: {
    agent_steps?: DebugStep[]
    tokens_used?: number
    latency_ms?: number
  }
}
