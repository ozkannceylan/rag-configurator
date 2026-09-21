"""MongoDB document models for vector storage."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IngestionStatus(StrEnum):
    """Status of an ingestion job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DocumentRecord(BaseModel):
    """MongoDB document model for processed files."""

    id: str | None = Field(None, alias="_id")
    config_id: str = Field(..., description="RAG pipeline configuration ID")
    ingestion_id: str = Field(..., description="Ingestion job ID")
    user_id: str = Field(..., description="User who owns this document")

    # File information
    file_path: str = Field(..., description="Original file path")
    file_name: str = Field(..., description="File name")
    file_type: str = Field(..., description="File extension/type")
    file_size_bytes: int = Field(0, description="File size in bytes")

    # Content tracking
    content_hash: str = Field(..., description="MD5 hash for deduplication")
    chunk_count: int = Field(0, description="Number of chunks created")

    # Processing info
    processor_name: str = Field("", description="Processor used")
    processing_time_ms: float = Field(0.0, description="Processing duration")

    # Timestamps
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_mongo(self) -> dict[str, Any]:
        """Convert to MongoDB document."""
        data = self.model_dump(exclude={"id"}, by_alias=True)
        if self.id:
            data["_id"] = self.id
        return data


class ChunkRecord(BaseModel):
    """MongoDB document model for text chunks with embeddings."""

    id: str | None = Field(None, alias="_id")
    config_id: str = Field(..., description="RAG pipeline configuration ID")
    document_id: str = Field(..., description="Parent document ID")
    ingestion_id: str = Field(..., description="Ingestion job ID")
    user_id: str = Field(..., description="User who owns this chunk")

    # Content
    content: str = Field(..., description="Chunk text content")
    content_hash: str = Field("", description="MD5 hash of content")

    # Embedding
    embedding: list[float] = Field(default_factory=list, description="Vector embedding")
    embedding_model: str = Field("", description="Model used for embedding")
    embedding_dimensions: int = Field(0, description="Embedding vector dimensions")

    # Position
    chunk_index: int = Field(0, description="Index within document")
    start_char: int = Field(0, description="Start character position")
    end_char: int = Field(0, description="End character position")

    # RBAC metadata
    folder_path: str = Field("", description="Source folder for access control")
    access_tags: list[str] = Field(
        default_factory=list, description="Access control tags"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_mongo(self) -> dict[str, Any]:
        """Convert to MongoDB document."""
        data = self.model_dump(exclude={"id"}, by_alias=True)
        if self.id:
            data["_id"] = self.id
        return data


class IngestionRecord(BaseModel):
    """MongoDB document model for ingestion jobs."""

    id: str | None = Field(None, alias="_id")
    config_id: str = Field(..., description="RAG pipeline configuration ID")
    user_id: str = Field(..., description="User who initiated ingestion")

    # Status
    status: IngestionStatus = Field(IngestionStatus.PENDING)
    celery_task_id: str | None = Field(None, description="Celery task ID")
    idempotency_key: str | None = Field(
        None,
        description="Stable key used to collapse duplicate ingestion starts",
    )
    data_source_hash: str | None = Field(
        None,
        description="Hash of the effective data source definition",
    )

    # Progress
    total_files: int = Field(0)
    processed_files: int = Field(0)
    failed_files: int = Field(0)
    total_chunks: int = Field(0)

    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Error tracking
    errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Configuration snapshot
    config_snapshot: dict[str, Any] = Field(
        default_factory=dict, description="Copy of config at ingestion time"
    )

    class Config:
        populate_by_name = True
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}

    def to_mongo(self) -> dict[str, Any]:
        """Convert to MongoDB document."""
        data = self.model_dump(exclude={"id"}, by_alias=True)
        if self.id:
            data["_id"] = self.id
        return data

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100

    @property
    def duration_seconds(self) -> float | None:
        """Calculate job duration in seconds."""
        if not self.started_at:
            return None
        end = self.completed_at or datetime.utcnow()
        return (end - self.started_at).total_seconds()


class SearchResult(BaseModel):
    """Result from vector similarity search."""

    chunk_id: str
    document_id: str
    config_id: str
    content: str
    score: float = Field(..., description="Similarity score")
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Document info
    file_name: str | None = None
    file_path: str | None = None
    chunk_index: int = 0
