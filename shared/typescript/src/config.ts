/**
 * Configuration types for RAG pipelines
 */

import {
  DataSourceType,
  DataType,
  LLMProvider,
  EmbeddingProvider,
  RetrievalMethod,
  AgentTemplate,
  ChunkingStrategy,
  IngestionStatus,
} from './enums';

// ==================== STEP 1: DATA SOURCE ====================

export interface FolderConfig {
  path: string;
  name: string;
  detected_types: DataType[];
  allowed_roles: string[];
  recursive: boolean;
  file_patterns: string[];
  file_count: number;
}

export interface DataSourceConfig {
  type: DataSourceType;
  base_path: string;
  credentials?: Record<string, string> | null;
  folders: FolderConfig[];
  has_multimodal: boolean;
}

// ==================== STEP 2: RBAC ====================

export interface RoleConfig {
  name: string;
  description: string;
  allowed_folders: string[];
  can_query: boolean;
  can_view_sources: boolean;
  rate_limit?: number | null;
}

export interface RBACConfig {
  enabled: boolean;
  roles: RoleConfig[];
  default_role: string;
}

// ==================== STEP 3: MODEL SELECTION ====================

export interface LLMConfig {
  provider: LLMProvider;
  model_name: string;
  base_url?: string | null;
  api_key?: string | null;
  temperature: number;
  max_tokens: number;
  is_multimodal: boolean;
}

export interface EmbeddingConfig {
  provider: EmbeddingProvider;
  model_name: string;
  base_url?: string | null;
  api_key?: string | null;
  dimensions: number;
}

export interface DocumentProcessingConfig {
  use_docling: boolean;
  use_vision_llm: boolean;
  vision_llm?: LLMConfig | null;
  ocr_enabled: boolean;
}

export interface ModelConfig {
  llm: LLMConfig;
  embedding: EmbeddingConfig;
  document_processing: DocumentProcessingConfig;
}

// ==================== STEP 4: RETRIEVAL ====================

export interface VectorSearchConfig {
  enabled: boolean;
  top_k: number;
  score_threshold: number;
}

export interface KeywordSearchConfig {
  enabled: boolean;
  top_k: number;
  use_fuzzy: boolean;
  boost_factor: number;
}

export interface GraphSearchConfig {
  enabled: boolean;
  max_depth: number;
  top_k: number;
}

export interface GraphSchemaNode {
  name: string;
  description: string;
  properties: string[];
}

export interface GraphSchemaRelation {
  name: string;
  source_node: string;
  target_node: string;
  description: string;
}

export interface GraphSchema {
  nodes: GraphSchemaNode[];
  relations: GraphSchemaRelation[];
  auto_extract: boolean;
}

export interface RetrievalConfig {
  method: RetrievalMethod;
  vector: VectorSearchConfig;
  keyword: KeywordSearchConfig;
  graph: GraphSearchConfig;
  graph_schema?: GraphSchema | null;
  reranker_enabled: boolean;
  reranker_model?: string | null;
}

// ==================== CHUNKING ====================

export interface ChunkingConfig {
  strategy: ChunkingStrategy;
  chunk_size: number;
  chunk_overlap: number;
  separators: string[];
}

// ==================== STEP 5: AGENT ====================

export interface AgentConfig {
  template: AgentTemplate;
  max_iterations: number;
  enable_judge: boolean;
  judge_llm?: LLMConfig | null;
}

// ==================== STEP 6: PROMPTS ====================

export interface PromptConfig {
  system_prompt: string;
  rag_prompt_template: string;
  judge_prompts?: Record<string, string> | null;
}

// ==================== MAIN CONFIG ====================

export interface RAGPipelineConfig {
  id?: string;
  name: string;
  description: string;
  version: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  status: IngestionStatus;
  api_endpoint?: string | null;
  data_source: DataSourceConfig;
  rbac: RBACConfig;
  models: ModelConfig;
  retrieval: RetrievalConfig;
  chunking: ChunkingConfig;
  agent: AgentConfig;
  prompts: PromptConfig;
  stats?: Record<string, any> | null;
}
