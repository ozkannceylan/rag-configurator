"""Base retriever interface and common types."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SourceType(str, Enum):
    """Type of retrieval source."""

    VECTOR = "vector"
    KEYWORD = "keyword"
    GRAPH = "graph"
    HYBRID = "hybrid"


@dataclass
class RetrievedChunk:
    """A retrieved chunk from the knowledge base."""

    # Core content
    content: str
    score: float

    # Identification
    chunk_id: str
    document_id: str
    config_id: str

    # Source information
    source_type: SourceType = SourceType.VECTOR

    # Document metadata
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None

    # Position within document
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0

    # RBAC metadata
    folder_path: Optional[str] = None
    access_tags: List[str] = field(default_factory=list)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "score": self.score,
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "config_id": self.config_id,
            "source_type": self.source_type.value,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "chunk_index": self.chunk_index,
            "folder_path": self.folder_path,
            "metadata": self.metadata,
        }

    @classmethod
    def from_mongo_doc(
        cls,
        doc: Dict[str, Any],
        score: float,
        source_type: SourceType = SourceType.VECTOR,
    ) -> "RetrievedChunk":
        """Create from MongoDB document."""
        return cls(
            content=doc.get("content", ""),
            score=score,
            chunk_id=str(doc.get("_id", "")),
            document_id=doc.get("document_id", ""),
            config_id=doc.get("config_id", ""),
            source_type=source_type,
            file_name=doc.get("file_name"),
            file_path=doc.get("file_path"),
            file_type=doc.get("file_type"),
            chunk_index=doc.get("chunk_index", 0),
            start_char=doc.get("start_char", 0),
            end_char=doc.get("end_char", 0),
            folder_path=doc.get("folder_path"),
            access_tags=doc.get("access_tags", []),
            metadata=doc.get("metadata", {}),
            created_at=doc.get("created_at"),
        )


@dataclass
class RetrievalConfig:
    """Configuration for retrieval."""

    # Basic settings
    top_k: int = 5
    min_score: float = 0.0

    # Embedding settings
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    # Filter settings
    folder_paths: Optional[List[str]] = None
    access_tags: Optional[List[str]] = None
    file_types: Optional[List[str]] = None

    # Search settings
    use_reranking: bool = False
    rerank_top_n: int = 10

    # MongoDB Vector Search settings
    vector_index_name: str = "vector_index"
    num_candidates: int = 100  # Number of candidates for ANN search

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetrievalConfig":
        """Create from dictionary."""
        return cls(
            top_k=data.get("top_k", 5),
            min_score=data.get("min_score", 0.0),
            embedding_provider=data.get("embedding_provider", "openai"),
            embedding_model=data.get("embedding_model", "text-embedding-3-small"),
            folder_paths=data.get("folder_paths"),
            access_tags=data.get("access_tags"),
            file_types=data.get("file_types"),
            use_reranking=data.get("use_reranking", False),
            rerank_top_n=data.get("rerank_top_n", 10),
            vector_index_name=data.get("vector_index_name", "vector_index"),
            num_candidates=data.get("num_candidates", 100),
        )


@dataclass
class RetrievalResult:
    """Result of a retrieval operation."""

    chunks: List[RetrievedChunk]
    query: str
    config_id: str

    # Statistics
    total_found: int = 0
    retrieval_time_ms: float = 0.0

    # Source breakdown
    source_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunks": [c.to_dict() for c in self.chunks],
            "query": self.query,
            "config_id": self.config_id,
            "total_found": self.total_found,
            "retrieval_time_ms": self.retrieval_time_ms,
            "source_counts": self.source_counts,
        }


class BaseRetriever(ABC):
    """Abstract base class for retrievers."""

    def __init__(self, config: Optional[RetrievalConfig] = None):
        """
        Initialize retriever.

        Args:
            config: Retrieval configuration
        """
        self.config = config or RetrievalConfig()

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        config_id: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: User query text
            config_id: RAG pipeline configuration ID
            top_k: Number of results to return (overrides config)
            filters: Additional filters to apply

        Returns:
            List of retrieved chunks sorted by relevance
        """
        pass

    async def retrieve_with_stats(
        self,
        query: str,
        config_id: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> RetrievalResult:
        """
        Retrieve with full statistics.

        Args:
            query: User query text
            config_id: RAG pipeline configuration ID
            top_k: Number of results to return
            filters: Additional filters to apply

        Returns:
            RetrievalResult with chunks and stats
        """
        import time

        start_time = time.time()

        chunks = await self.retrieve(
            query=query,
            config_id=config_id,
            top_k=top_k,
            filters=filters,
        )

        retrieval_time = (time.time() - start_time) * 1000

        # Count by source type
        source_counts: Dict[str, int] = {}
        for chunk in chunks:
            source = chunk.source_type.value
            source_counts[source] = source_counts.get(source, 0) + 1

        return RetrievalResult(
            chunks=chunks,
            query=query,
            config_id=config_id,
            total_found=len(chunks),
            retrieval_time_ms=retrieval_time,
            source_counts=source_counts,
        )

    def _apply_score_threshold(
        self, chunks: List[RetrievedChunk], min_score: Optional[float] = None
    ) -> List[RetrievedChunk]:
        """Filter chunks by minimum score."""
        threshold = min_score if min_score is not None else self.config.min_score
        return [c for c in chunks if c.score >= threshold]
