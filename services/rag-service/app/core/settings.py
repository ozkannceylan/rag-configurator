"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service Configuration
    service_name: str = "rag-service"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    port: int = Field(default=8003, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # MongoDB Configuration
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        alias="MONGODB_URI",
    )
    mongodb_database: str = Field(
        default="rag_configurator",
        alias="MONGODB_DATABASE",
    )

    # Redis Configuration (for caching and session management)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )

    # LLM Provider Configuration
    default_llm_provider: str = Field(default="openai", alias="DEFAULT_LLM_PROVIDER")
    default_llm_model: str = Field(default="gpt-4o-mini", alias="DEFAULT_LLM_MODEL")

    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_organization: Optional[str] = Field(default=None, alias="OPENAI_ORGANIZATION")
    openai_base_url: Optional[str] = Field(default=None, alias="OPENAI_BASE_URL")

    # Anthropic Configuration
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Ollama Configuration (local models)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_BASE_URL",
    )
    ollama_default_model: str = Field(
        default="llama3.2",
        alias="OLLAMA_DEFAULT_MODEL",
    )

    # vLLM Configuration (self-hosted inference)
    vllm_base_url: Optional[str] = Field(default=None, alias="VLLM_BASE_URL")
    vllm_api_key: Optional[str] = Field(default=None, alias="VLLM_API_KEY")

    # Embedding Configuration
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="EMBEDDING_MODEL",
    )
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")

    # RAG Configuration
    default_top_k: int = Field(default=5, alias="DEFAULT_TOP_K")
    default_min_score: float = Field(default=0.7, alias="DEFAULT_MIN_SCORE")
    max_context_tokens: int = Field(default=4000, alias="MAX_CONTEXT_TOKENS")
    max_response_tokens: int = Field(default=2000, alias="MAX_RESPONSE_TOKENS")

    # Streaming Configuration
    enable_streaming: bool = Field(default=True, alias="ENABLE_STREAMING")
    stream_chunk_size: int = Field(default=10, alias="STREAM_CHUNK_SIZE")

    # MLflow Configuration (optional, for experiment tracking)
    mlflow_tracking_uri: Optional[str] = Field(default=None, alias="MLFLOW_TRACKING_URI")
    mlflow_experiment_name: str = Field(
        default="rag-experiments",
        alias="MLFLOW_EXPERIMENT_NAME",
    )

    # CORS Configuration - use Union to prevent pydantic-settings from JSON parsing
    cors_origins: Union[str, List[str]] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS",
    )

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    # Timeout Configuration
    llm_timeout_seconds: float = Field(default=60.0, alias="LLM_TIMEOUT_SECONDS")
    retrieval_timeout_seconds: float = Field(default=10.0, alias="RETRIEVAL_TIMEOUT_SECONDS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            # Handle comma-separated string
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://localhost:5173"]

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ("development", "dev", "local")

    @property
    def mlflow_enabled(self) -> bool:
        """Check if MLflow tracking is enabled."""
        return self.mlflow_tracking_uri is not None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
