"""Enumeration types for RAG Configurator."""

from enum import Enum


class DataSourceType(str, Enum):
    """Supported data source types."""
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"


class DataType(str, Enum):
    """Supported data/file types."""
    TEXT = "text"
    PDF = "pdf"
    IMAGE = "image"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    MARKDOWN = "markdown"


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    VLLM = "vllm"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"


class RetrievalMethod(str, Enum):
    """Retrieval strategy types."""
    NAIVE = "naive"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    GRAPH = "graph"
    HYBRID_GRAPH = "hybrid_graph"


class AgentTemplate(str, Enum):
    """Predefined agent templates."""
    NAIVE_RAG = "naive_rag"
    REACT = "react"
    CRAG = "crag"
    SELF_RAG = "self_rag"
    MULTI_QUERY = "multi_query"
    PLAN_SOLVE = "plan_solve"


class ChunkingStrategy(str, Enum):
    """Text chunking strategies."""
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    DOCUMENT = "document"


class IngestionStatus(str, Enum):
    """Ingestion job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
