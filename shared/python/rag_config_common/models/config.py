"""Configuration models for RAG pipelines."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

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


# ==================== STEP 1: DATA SOURCE ====================

class FolderConfig(BaseModel):
    """Configuration for a single data folder."""
    path: str = Field(..., description="Relative path from base")
    name: str = Field(..., description="Display name")
    detected_types: List[DataType] = Field(
        default_factory=list,
        description="Auto-detected file types"
    )
    allowed_roles: List[str] = Field(
        default=["*"],
        description="Roles that can access this folder (* = all)"
    )
    recursive: bool = Field(default=True, description="Include subfolders")
    file_patterns: List[str] = Field(
        default=["*"],
        description="Glob patterns for file matching"
    )
    file_count: int = Field(default=0, description="Number of files detected")


class DataSourceConfig(BaseModel):
    """Step 1: Data source configuration."""
    type: DataSourceType
    base_path: str = Field(..., description="Root path for data")
    credentials: Optional[Dict[str, str]] = Field(
        default=None,
        description="Cloud credentials (encrypted)"
    )
    folders: List[FolderConfig] = Field(default_factory=list)
    has_multimodal: bool = Field(
        default=False,
        description="True if images/complex PDFs detected"
    )


# ==================== STEP 2: RBAC ====================

class RoleConfig(BaseModel):
    """Single role definition."""
    name: str = Field(..., description="Role identifier")
    description: str = Field(default="")
    allowed_folders: List[str] = Field(
        default=["*"],
        description="Folder paths this role can access"
    )
    can_query: bool = Field(default=True)
    can_view_sources: bool = Field(default=True)
    rate_limit: Optional[int] = Field(
        default=None,
        description="Max queries per minute"
    )


class RBACConfig(BaseModel):
    """Step 2: RBAC configuration (optional)."""
    enabled: bool = Field(default=False)
    roles: List[RoleConfig] = Field(default_factory=list)
    default_role: str = Field(default="user")


# ==================== STEP 3: MODEL SELECTION ====================

class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: LLMProvider
    model_name: str
    base_url: Optional[str] = Field(
        default=None,
        description="For Ollama/vLLM/custom endpoints"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key (encrypted in storage)"
    )
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1)
    is_multimodal: bool = Field(default=False)


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""
    provider: EmbeddingProvider
    model_name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    dimensions: int = Field(default=1536)


class DocumentProcessingConfig(BaseModel):
    """Document processing options."""
    use_docling: bool = Field(
        default=False,
        description="Use Docling for PDF structure extraction"
    )
    use_vision_llm: bool = Field(
        default=False,
        description="Use vision LLM for images/complex docs"
    )
    vision_llm: Optional[LLMConfig] = None
    ocr_enabled: bool = Field(default=True)


class ModelConfig(BaseModel):
    """Step 3: Combined model configuration."""
    llm: LLMConfig
    embedding: EmbeddingConfig
    document_processing: DocumentProcessingConfig = Field(
        default_factory=DocumentProcessingConfig
    )


# ==================== STEP 4: RETRIEVAL ====================

class VectorSearchConfig(BaseModel):
    """Vector search settings."""
    enabled: bool = True
    top_k: int = Field(default=5, ge=1, le=100)
    score_threshold: float = Field(default=0.7, ge=0, le=1)


class KeywordSearchConfig(BaseModel):
    """Atlas Search / keyword settings."""
    enabled: bool = False
    top_k: int = Field(default=5, ge=1, le=100)
    use_fuzzy: bool = True
    boost_factor: float = Field(default=1.0, description="Weight for hybrid scoring")


class GraphSearchConfig(BaseModel):
    """Graph RAG settings."""
    enabled: bool = False
    max_depth: int = Field(default=2, ge=1, le=5)
    top_k: int = Field(default=5, ge=1, le=100)


class GraphSchemaNode(BaseModel):
    """Node type definition for knowledge graph."""
    name: str = Field(..., description="Node type name (e.g., Person, Company)")
    description: str = Field(default="")
    properties: List[str] = Field(
        default_factory=list,
        description="Expected properties"
    )


class GraphSchemaRelation(BaseModel):
    """Relation type definition for knowledge graph."""
    name: str = Field(..., description="Relation name (e.g., WORKS_FOR)")
    source_node: str = Field(..., description="Source node type")
    target_node: str = Field(..., description="Target node type")
    description: str = Field(default="")


class GraphSchema(BaseModel):
    """Knowledge graph schema definition."""
    nodes: List[GraphSchemaNode] = Field(default_factory=list)
    relations: List[GraphSchemaRelation] = Field(default_factory=list)
    auto_extract: bool = Field(
        default=True,
        description="Let LLM automatically extract entities"
    )


class RetrievalConfig(BaseModel):
    """Step 4: Retrieval configuration."""
    method: RetrievalMethod
    vector: VectorSearchConfig = Field(default_factory=VectorSearchConfig)
    keyword: KeywordSearchConfig = Field(default_factory=KeywordSearchConfig)
    graph: GraphSearchConfig = Field(default_factory=GraphSearchConfig)
    graph_schema: Optional[GraphSchema] = None
    reranker_enabled: bool = False
    reranker_model: Optional[str] = None


# ==================== CHUNKING ====================

class ChunkingConfig(BaseModel):
    """Chunking strategy configuration."""
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = Field(default=512, ge=100, le=4000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    separators: List[str] = Field(default=["\n\n", "\n", " ", ""])


# ==================== STEP 5: AGENT ====================

class AgentConfig(BaseModel):
    """Step 5: Agent template configuration."""
    template: AgentTemplate
    max_iterations: int = Field(default=5, ge=1, le=20)
    enable_judge: bool = Field(
        default=False,
        description="Enable LLM-as-judge evaluation"
    )
    judge_llm: Optional[LLMConfig] = None


# ==================== STEP 6: PROMPTS ====================

class PromptConfig(BaseModel):
    """Step 6: Prompt configuration."""
    system_prompt: str = Field(..., description="System prompt for the LLM")
    rag_prompt_template: str = Field(
        ...,
        description="RAG prompt with {context} and {query} placeholders"
    )
    judge_prompts: Optional[Dict[str, str]] = Field(
        default=None,
        description="Prompts for evaluation (relevance, faithfulness, etc.)"
    )


# ==================== MAIN CONFIG ====================

class RAGPipelineConfig(BaseModel):
    """
    Complete RAG pipeline configuration.
    This is the main document stored in MongoDB.
    """
    # Metadata
    id: Optional[str] = Field(default=None, alias="_id")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    version: str = Field(default="1.0.0")
    created_by: str = Field(..., description="User ID of creator")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Status
    status: IngestionStatus = Field(default=IngestionStatus.PENDING)
    api_endpoint: Optional[str] = Field(
        default=None,
        description="Generated API endpoint path"
    )
    
    # Configuration Steps
    data_source: DataSourceConfig
    rbac: RBACConfig = Field(default_factory=RBACConfig)
    models: ModelConfig
    retrieval: RetrievalConfig
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    agent: AgentConfig
    prompts: PromptConfig
    
    # Ingestion Stats
    stats: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Ingestion statistics (document count, chunk count, etc.)"
    )

    model_config = {
        "populate_by_name": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }
