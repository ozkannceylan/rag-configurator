/**
 * API request/response types
 */

import { RAGPipelineConfig } from './config';
import { IngestionStatus } from './enums';
import { User } from './user';

// ========== Auth ==========

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface UserResponse extends Omit<User, 'password_hash'> {}

// ========== Config ==========

export interface ConfigListResponse {
  items: ConfigSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface ConfigSummary {
  id: string;
  name: string;
  description: string;
  status: IngestionStatus;
  created_at: string;
  updated_at: string;
}

export interface ConfigCreateRequest extends Omit<RAGPipelineConfig, 'id' | 'created_by' | 'created_at' | 'updated_at' | 'status' | 'api_endpoint' | 'stats'> {}

// ========== Ingestion ==========

export interface IngestionStatusResponse {
  config_id: string;
  status: IngestionStatus;
  progress: number;
  current_step: string;
  steps_completed: string[];
  error?: string;
  stats?: IngestionStats;
}

export interface IngestionStats {
  total_files: number;
  processed_files: number;
  total_chunks: number;
  total_embeddings: number;
  graph_nodes?: number;
  graph_edges?: number;
  processing_time_seconds: number;
}

// ========== RAG Query ==========

export interface QueryRequest {
  query: string;
  config_id?: string;
  user_role?: string;
  include_sources?: boolean;
  include_debug?: boolean;
}

export interface QueryResponse {
  answer: string;
  sources?: Source[];
  debug?: DebugInfo;
}

export interface Source {
  content: string;
  metadata: Record<string, any>;
  score: number;
  source_type: 'vector' | 'keyword' | 'graph';
}

export interface DebugInfo {
  retrieval_time_ms: number;
  generation_time_ms: number;
  agent_steps?: AgentStep[];
  retrieved_chunks: number;
}

export interface AgentStep {
  step: number;
  action: string;
  observation: string;
  thought?: string;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  config_id?: string;
  user_role?: string;
}

export interface ChatResponse {
  answer: string;
  conversation_id: string;
  sources?: Source[];
}

// ========== Standard Response ==========

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: APIError;
  meta?: ResponseMeta;
}

export interface APIError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

export interface ResponseMeta {
  request_id: string;
  timestamp: string;
  version: string;
}
