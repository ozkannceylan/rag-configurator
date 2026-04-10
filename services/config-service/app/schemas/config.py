"""Configuration schemas for request/response."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from rag_config_common.models.enums import IngestionStatus
from rag_config_common.models.config import (
    DataSourceConfig,
    RBACConfig,
    ModelConfig,
    RetrievalConfig,
    ChunkingConfig,
    AgentConfig,
    PromptConfig,
    GuardrailsConfig,
    EvaluationConfig,
    CacheConfig,
)


class ConfigCreate(BaseModel):
    """Configuration creation request."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    data_source: DataSourceConfig
    rbac: Optional[RBACConfig] = None
    models: ModelConfig
    retrieval: RetrievalConfig
    chunking: Optional[ChunkingConfig] = None
    agent: AgentConfig
    prompts: PromptConfig
    guardrails: Optional[GuardrailsConfig] = None
    evaluation: Optional[EvaluationConfig] = None
    cache: Optional[CacheConfig] = None


class ConfigUpdate(BaseModel):
    """Configuration update request."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    data_source: Optional[DataSourceConfig] = None
    rbac: Optional[RBACConfig] = None
    models: Optional[ModelConfig] = None
    retrieval: Optional[RetrievalConfig] = None
    chunking: Optional[ChunkingConfig] = None
    agent: Optional[AgentConfig] = None
    prompts: Optional[PromptConfig] = None
    guardrails: Optional[GuardrailsConfig] = None
    evaluation: Optional[EvaluationConfig] = None
    cache: Optional[CacheConfig] = None


class ConfigSummary(BaseModel):
    """Configuration summary for list views."""

    id: str
    name: str
    description: str
    status: IngestionStatus
    created_at: datetime
    updated_at: datetime


class ConfigResponse(BaseModel):
    """Full configuration response."""

    id: str
    name: str
    description: str
    version: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    status: IngestionStatus
    api_endpoint: Optional[str] = None
    data_source: DataSourceConfig
    rbac: RBACConfig
    models: ModelConfig
    retrieval: RetrievalConfig
    chunking: ChunkingConfig
    agent: AgentConfig
    prompts: PromptConfig
    guardrails: Optional[GuardrailsConfig] = None
    evaluation: Optional[EvaluationConfig] = None
    cache: Optional[CacheConfig] = None
    stats: Optional[dict] = None


class ConfigListResponse(BaseModel):
    """Paginated configuration list response."""

    items: List[ConfigSummary]
    total: int
    page: int
    page_size: int
