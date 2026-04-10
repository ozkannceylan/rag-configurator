"""RAG Configurator Common - Shared models and utilities."""

from rag_config_common.auth import (
    TokenBlacklist,
    ServiceAuthMiddleware,
    build_signed_headers,
    decode_token,
    extract_bearer_token,
    get_authenticated_user_id,
    get_token_jti,
    get_token_ttl_seconds,
    sign_request,
    verify_request_auth,
)
from rag_config_common.models.config import (
    RAGPipelineConfig,
    DataSourceConfig,
    RBACConfig,
    ModelConfig,
    RetrievalConfig,
    GuardrailsConfig,
    ChunkingConfig,
    AgentConfig,
    PromptConfig,
    EvaluationConfig,
    CacheConfig,
)
from rag_config_common.models.user import User
from rag_config_common.observability import setup_tracing
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
    "GuardrailsConfig",
    "ChunkingConfig",
    "AgentConfig",
    "PromptConfig",
    "EvaluationConfig",
    "CacheConfig",
    # Shared auth
    "TokenBlacklist",
    "ServiceAuthMiddleware",
    "build_signed_headers",
    "decode_token",
    "extract_bearer_token",
    "get_authenticated_user_id",
    "get_token_jti",
    "get_token_ttl_seconds",
    "sign_request",
    "verify_request_auth",
    # User model
    "User",
    # Observability
    "setup_tracing",
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
