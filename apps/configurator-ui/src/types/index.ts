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

export interface RegisterRequest {
  email: string
  password: string
  name: string
}

// RAG Config types
export interface RAGConfig {
  id?: string
  name: string
  description?: string
  data_source: DataSourceConfig
  rbac?: RBACConfig
  models: ModelsConfig
  retrieval: RetrievalConfig
  chunking: ChunkingConfig
  agent: AgentConfig
  prompts: PromptsConfig
  guardrails?: GuardrailsConfig
  evaluation?: EvaluationConfig
  cache?: CacheConfig
  created_at?: string
  updated_at?: string
  status?: 'draft' | 'ready' | 'processing' | 'error'
}

export interface FolderConfig {
  path: string
  name: string
  detected_types?: string[]
  allowed_roles?: string[]
  recursive?: boolean
  file_patterns?: string[]
  file_count?: number
}

export interface DataSourceConfig {
  type: 'local' | 's3' | 'gcs' | 'azure_blob'
  base_path: string
  bucket?: string
  prefix?: string
  region?: string
  credentials?: Record<string, string>
  folders: FolderConfig[]
  has_multimodal?: boolean
}

export interface RoleConfig {
  name: string
  description?: string
  allowed_folders?: string[]
  can_query?: boolean
  can_view_sources?: boolean
  rate_limit?: number
}

export interface RBACConfig {
  enabled: boolean
  roles: RoleConfig[]
  default_role: string
}

export interface DocumentProcessingConfig {
  use_docling?: boolean
  use_vision_llm?: boolean
  vision_llm?: LLMConfig
  ocr_enabled?: boolean
}

export interface ModelsConfig {
  llm: LLMConfig
  embedding: EmbeddingConfig
  document_processing?: DocumentProcessingConfig
}

export interface LLMConfig {
  provider: 'openai' | 'anthropic' | 'ollama' | 'vllm' | 'azure_openai'
  model_name: string
  api_key?: string
  base_url?: string
  temperature: number
  max_tokens: number
  is_multimodal?: boolean
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
    enabled?: boolean
    top_k: number
    score_threshold: number
  }
  keyword?: {
    enabled: boolean
    top_k?: number
    use_fuzzy: boolean
    boost_factor: number
  }
  graph?: {
    enabled: boolean
    max_depth: number
    top_k?: number
  }
  graph_schema?: GraphSchema
  reranker_enabled?: boolean
  reranker_model?: string
}

export interface GraphSchema {
  auto_extract: boolean
  nodes: NodeType[]
  relations: RelationType[]
}

export interface NodeType {
  name: string
  description: string
  properties?: Record<string, string>
}

export interface RelationType {
  name: string
  source_type: string
  target_type: string
  description: string
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
  enable_judge?: boolean
  judge_llm?: LLMConfig
  temperature_override?: number
  config?: Record<string, string | number | boolean>
}

export interface PromptsConfig {
  system_prompt: string
  rag_prompt_template: string
}

export interface GuardrailsConfig {
  enabled: boolean
  prompt_injection: boolean
  pii: boolean
  toxicity: boolean
  fail_closed: boolean
}

export interface EvaluationConfig {
  enabled: boolean
  async_mode: boolean
  sample_rate: number
}

export interface CacheConfig {
  enabled: boolean
  embedding_cache_ttl: number
  query_cache_ttl: number
}

// API response types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// Ingestion types
export interface IngestionStatus {
  config_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  current_step: string
  // Flat counters returned by newer ingestion responses; older ones nest them
  // under `stats`, which is why the views read both.
  processed_files?: number
  failed_files?: number
  total_chunks?: number
  stats?: {
    files_processed: number
    failed_files?: number
    total_files?: number
    chunks_created: number
    embeddings_generated: number
    nodes_created?: number
    edges_created?: number
  }
  error?: string
  started_at?: string
  completed_at?: string
}

export interface LogEntry {
  timestamp: string
  level: 'INFO' | 'WARN' | 'ERROR'
  message: string
}

// Folder scanning
export interface FolderStructure {
  path: string
  name: string
  type: 'folder' | 'file'
  children?: FolderStructure[]
  file_count?: number
}

/**
 * The shape the configuration wizard works with.
 *
 * `RAGConfig` marks many sections optional because a config coming back from
 * the API may omit them. The wizard never sees a config in that state: the
 * store seeds every section from its defaults and merges any loaded config on
 * top of them (see `hydrateConfig` in `stores/wizard.ts`), so each step can
 * bind straight to `config.<section>.<field>` without guards.
 */
export type WizardConfig = RAGConfig & {
  rbac: RBACConfig
  models: ModelsConfig & {
    document_processing: DocumentProcessingConfig
  }
  retrieval: RetrievalConfig & {
    keyword: NonNullable<RetrievalConfig['keyword']>
    graph: NonNullable<RetrievalConfig['graph']>
  }
  agent: AgentConfig & {
    config: Record<string, string | number | boolean>
  }
}
