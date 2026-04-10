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
        populate_by_name=True,
    )

    # Service Configuration
    service_name: str = "ingestion-service"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    port: int = Field(default=8002, alias="PORT")
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

    # Redis Configuration (for Celery broker and result backend)
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )

    # Inter-service auth
    inter_service_secret: str = Field(
        default="change-this-inter-service-secret",
        alias="INTER_SERVICE_SECRET",
    )

    # OpenTelemetry
    otel_exporter_otlp_endpoint: Optional[str] = Field(
        default=None,
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    otel_service_name: str = Field(
        default="ingestion-service",
        alias="OTEL_SERVICE_NAME",
    )

    # Celery Configuration
    celery_broker_url: Optional[str] = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: Optional[str] = Field(
        default=None, alias="CELERY_RESULT_BACKEND"
    )
    celery_task_default_queue: str = Field(
        default="ingestion", alias="CELERY_TASK_DEFAULT_QUEUE"
    )

    # Embedding Provider Configuration
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(
        default="text-embedding-3-small", alias="EMBEDDING_MODEL"
    )
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")

    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    # Ollama Configuration
    ollama_base_url: str = Field(
        default="http://host.docker.internal:11434",
        alias="OLLAMA_BASE_URL",
    )

    # Vector Store Configuration
    vector_store_type: str = Field(default="chroma", alias="VECTOR_STORE_TYPE")
    chroma_host: str = Field(default="localhost", alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, alias="CHROMA_PORT")
    chroma_persist_directory: str = Field(
        default="./chroma_data", alias="CHROMA_PERSIST_DIRECTORY"
    )

    # Config Service URL (for fetching pipeline configurations)
    config_service_url: str = Field(
        default="http://localhost:8001",
        alias="CONFIG_SERVICE_URL",
    )

    # CORS Configuration - use Union to prevent pydantic-settings from JSON parsing
    cors_origins: Union[str, List[str]] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS",
    )

    # Processing Configuration
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    max_concurrent_tasks: int = Field(default=4, alias="MAX_CONCURRENT_TASKS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def celery_broker(self) -> str:
        """Get Celery broker URL, falling back to Redis URL."""
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        """Get Celery result backend URL, falling back to Redis URL."""
        return self.celery_result_backend or self.redis_url

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ("development", "dev", "local")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
