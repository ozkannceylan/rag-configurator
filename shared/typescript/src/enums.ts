/**
 * Enumeration types for RAG Configurator
 */

export enum DataSourceType {
  LOCAL = 'local',
  S3 = 's3',
  GCS = 'gcs',
  AZURE_BLOB = 'azure_blob',
}

export enum DataType {
  TEXT = 'text',
  PDF = 'pdf',
  IMAGE = 'image',
  DOCX = 'docx',
  XLSX = 'xlsx',
  CSV = 'csv',
  MARKDOWN = 'markdown',
}

export enum LLMProvider {
  OPENAI = 'openai',
  OLLAMA = 'ollama',
  VLLM = 'vllm',
  ANTHROPIC = 'anthropic',
  AZURE_OPENAI = 'azure_openai',
}

export enum EmbeddingProvider {
  OPENAI = 'openai',
  OLLAMA = 'ollama',
  HUGGINGFACE = 'huggingface',
}

export enum RetrievalMethod {
  NAIVE = 'naive',
  KEYWORD = 'keyword',
  HYBRID = 'hybrid',
  GRAPH = 'graph',
  HYBRID_GRAPH = 'hybrid_graph',
}

export enum AgentTemplate {
  NAIVE_RAG = 'naive_rag',
  REACT = 'react',
  CRAG = 'crag',
  SELF_RAG = 'self_rag',
  MULTI_QUERY = 'multi_query',
  PLAN_SOLVE = 'plan_solve',
}

export enum ChunkingStrategy {
  RECURSIVE = 'recursive',
  SEMANTIC = 'semantic',
  DOCUMENT = 'document',
}

export enum IngestionStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}
