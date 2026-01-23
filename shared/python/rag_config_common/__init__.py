"""RAG Configurator Common - Shared models and utilities."""

from rag_config_common.models.config import (
    RAGPipelineConfig,
    DataSourceConfig,
    RBACConfig,
    ModelConfig,
    RetrievalConfig,
    ChunkingConfig,
    AgentConfig,
    PromptConfig,
)
from rag_config_common.models.user import User
from rag_config_common.models.enums import (
    DataSourceType,
    DataType,
    LLMProvider,
    EmbeddingProvider,
    RetrievalMethod,
    AgentTemplate,
    ChunkingStrategy,
    IngestionStatus,
)

__version__ = "0.1.0"

__all__ = [
    # Config models
    "RAGPipelineConfig",
    "DataSourceConfig",
    "RBACConfig",
    "ModelConfig",
    "RetrievalConfig",
    "ChunkingConfig",
    "AgentConfig",
    "PromptConfig",
    # User model
    "User",
    # Enums
    "DataSourceType",
    "DataType",
    "LLMProvider",
    "EmbeddingProvider",
    "RetrievalMethod",
    "AgentTemplate",
    "ChunkingStrategy",
    "IngestionStatus",
]
