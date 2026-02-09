"""Tests for retrieval module."""

import math
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.retrieval.base import (
    BaseRetriever,
    RetrievalConfig,
    RetrievalResult,
    RetrievedChunk,
    SourceType,
)
from app.retrieval.vector import VectorRetriever
from app.retrieval.embedder import QueryEmbedder


class TestRetrievedChunk:
    """Tests for RetrievedChunk."""

    def test_create_chunk(self):
        """Test creating a retrieved chunk."""
        chunk = RetrievedChunk(
            content="Test content",
            score=0.95,
            chunk_id="chunk-123",
            document_id="doc-456",
            config_id="config-789",
        )

        assert chunk.content == "Test content"
        assert chunk.score == 0.95
        assert chunk.chunk_id == "chunk-123"
        assert chunk.source_type == SourceType.VECTOR

    def test_chunk_to_dict(self):
        """Test converting chunk to dictionary."""
        chunk = RetrievedChunk(
            content="Test content",
            score=0.85,
            chunk_id="chunk-123",
            document_id="doc-456",
            config_id="config-789",
            file_name="test.pdf",
            chunk_index=3,
        )

        data = chunk.to_dict()

        assert data["content"] == "Test content"
        assert data["score"] == 0.85
        assert data["file_name"] == "test.pdf"
        assert data["source_type"] == "vector"

    def test_chunk_from_mongo_doc(self):
        """Test creating chunk from MongoDB document."""
        doc = {
            "_id": "chunk-123",
            "content": "Mongo content",
            "document_id": "doc-456",
            "config_id": "config-789",
            "chunk_index": 2,
            "folder_path": "/data/folder1",
            "access_tags": ["admin"],
            "metadata": {"key": "value"},
        }

        chunk = RetrievedChunk.from_mongo_doc(doc, score=0.9)

        assert chunk.chunk_id == "chunk-123"
        assert chunk.content == "Mongo content"
        assert chunk.score == 0.9
        assert chunk.folder_path == "/data/folder1"
        assert "admin" in chunk.access_tags

    def test_chunk_with_all_fields(self):
        """Test chunk with all fields populated."""
        chunk = RetrievedChunk(
            content="Full content",
            score=0.99,
            chunk_id="chunk-123",
            document_id="doc-456",
            config_id="config-789",
            source_type=SourceType.HYBRID,
            file_name="document.pdf",
            file_path="/path/to/document.pdf",
            file_type=".pdf",
            chunk_index=5,
            start_char=100,
            end_char=500,
            folder_path="/secure",
            access_tags=["user", "admin"],
            metadata={"custom": "data"},
        )

        assert chunk.source_type == SourceType.HYBRID
        assert chunk.file_type == ".pdf"
        assert chunk.start_char == 100
        assert len(chunk.access_tags) == 2


class TestRetrievalConfig:
    """Tests for RetrievalConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = RetrievalConfig()

        assert config.top_k == 5
        assert config.min_score == 0.0
        assert config.embedding_provider == "openai"
        assert config.use_reranking is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = RetrievalConfig(
            top_k=10,
            min_score=0.7,
            embedding_provider="ollama",
            embedding_model="nomic-embed-text",
            folder_paths=["/data/allowed"],
            use_reranking=True,
        )

        assert config.top_k == 10
        assert config.min_score == 0.7
        assert config.embedding_provider == "ollama"
        assert "/data/allowed" in config.folder_paths

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "top_k": 8,
            "min_score": 0.5,
            "embedding_provider": "openai",
            "folder_paths": ["/folder1", "/folder2"],
        }

        config = RetrievalConfig.from_dict(data)

        assert config.top_k == 8
        assert config.min_score == 0.5
        assert len(config.folder_paths) == 2


class TestRetrievalResult:
    """Tests for RetrievalResult."""

    def test_create_result(self):
        """Test creating retrieval result."""
        chunks = [
            RetrievedChunk(
                content="Chunk 1",
                score=0.9,
                chunk_id="c1",
                document_id="d1",
                config_id="cfg",
            ),
            RetrievedChunk(
                content="Chunk 2",
                score=0.8,
                chunk_id="c2",
                document_id="d1",
                config_id="cfg",
            ),
        ]

        result = RetrievalResult(
            chunks=chunks,
            query="test query",
            config_id="config-123",
            total_found=2,
            retrieval_time_ms=50.5,
        )

        assert len(result.chunks) == 2
        assert result.total_found == 2
        assert result.retrieval_time_ms == 50.5

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = RetrievalResult(
            chunks=[],
            query="test",
            config_id="cfg",
            total_found=0,
            source_counts={"vector": 3, "keyword": 2},
        )

        data = result.to_dict()

        assert data["query"] == "test"
        assert data["source_counts"]["vector"] == 3


class TestSourceType:
    """Tests for SourceType enum."""

    def test_source_types(self):
        """Test source type values."""
        assert SourceType.VECTOR.value == "vector"
        assert SourceType.KEYWORD.value == "keyword"
        assert SourceType.GRAPH.value == "graph"
        assert SourceType.HYBRID.value == "hybrid"


class TestVectorRetriever:
    """Tests for VectorRetriever."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=MagicMock())
        return db

    @pytest.fixture
    def retriever(self, mock_db):
        """Create a retriever with mock database."""
        config = RetrievalConfig(top_k=5, min_score=0.5)
        return VectorRetriever(db=mock_db, config=config)

    def test_create_retriever(self, mock_db):
        """Test creating a vector retriever."""
        retriever = VectorRetriever(db=mock_db)

        assert retriever.db == mock_db
        assert retriever.config.top_k == 5

    def test_create_retriever_with_config(self, mock_db):
        """Test creating retriever with custom config."""
        config = RetrievalConfig(top_k=10, min_score=0.7)
        retriever = VectorRetriever(db=mock_db, config=config)

        assert retriever.config.top_k == 10
        assert retriever.config.min_score == 0.7

    def test_cosine_similarity_identical(self, retriever):
        """Test cosine similarity with identical vectors."""
        vec = [1.0, 0.0, 0.0]
        similarity = retriever._cosine_similarity(vec, vec)
        assert similarity == 1.0

    def test_cosine_similarity_orthogonal(self, retriever):
        """Test cosine similarity with orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = retriever._cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_cosine_similarity_opposite(self, retriever):
        """Test cosine similarity with opposite vectors."""
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        similarity = retriever._cosine_similarity(vec1, vec2)
        assert similarity == -1.0

    def test_cosine_similarity_different_lengths(self, retriever):
        """Test cosine similarity with different length vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0]
        similarity = retriever._cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_cosine_similarity_zero_vector(self, retriever):
        """Test cosine similarity with zero vector."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = retriever._cosine_similarity(vec1, vec2)
        assert similarity == 0.0

    def test_apply_score_threshold(self, retriever):
        """Test applying score threshold filter."""
        chunks = [
            RetrievedChunk(
                content="High", score=0.9, chunk_id="1",
                document_id="d", config_id="c"
            ),
            RetrievedChunk(
                content="Low", score=0.3, chunk_id="2",
                document_id="d", config_id="c"
            ),
            RetrievedChunk(
                content="Medium", score=0.6, chunk_id="3",
                document_id="d", config_id="c"
            ),
        ]

        filtered = retriever._apply_score_threshold(chunks)

        assert len(filtered) == 2
        assert all(c.score >= 0.5 for c in filtered)


class TestQueryEmbedder:
    """Tests for QueryEmbedder."""

    def test_create_embedder(self):
        """Test creating an embedder."""
        embedder = QueryEmbedder(
            provider="openai",
            model="text-embedding-3-small",
        )

        assert embedder.provider == "openai"
        assert embedder.model == "text-embedding-3-small"

    def test_create_ollama_embedder(self):
        """Test creating Ollama embedder."""
        embedder = QueryEmbedder(
            provider="ollama",
            model="nomic-embed-text",
            base_url="http://localhost:11434",
        )

        assert embedder.provider == "ollama"
        assert embedder.base_url == "http://localhost:11434"

    @pytest.mark.asyncio
    async def test_embed_empty_query(self):
        """Test embedding empty query returns empty list."""
        embedder = QueryEmbedder()
        result = await embedder.embed_query("")
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_batch_empty(self):
        """Test embedding empty batch returns empty list."""
        embedder = QueryEmbedder()
        result = await embedder.embed_batch([])
        assert result == []


class TestBaseRetriever:
    """Tests for BaseRetriever abstract class."""

    def test_cannot_instantiate_base(self):
        """Test that BaseRetriever cannot be directly instantiated."""
        with pytest.raises(TypeError):
            BaseRetriever()

    def test_apply_score_threshold(self):
        """Test score threshold filtering in base class."""

        class ConcreteRetriever(BaseRetriever):
            async def retrieve(self, query, config_id, top_k=None, filters=None):
                return []

        retriever = ConcreteRetriever(RetrievalConfig(min_score=0.6))
        chunks = [
            RetrievedChunk(
                content="A", score=0.9, chunk_id="1",
                document_id="d", config_id="c"
            ),
            RetrievedChunk(
                content="B", score=0.4, chunk_id="2",
                document_id="d", config_id="c"
            ),
        ]

        filtered = retriever._apply_score_threshold(chunks)

        assert len(filtered) == 1
        assert filtered[0].content == "A"

    @pytest.mark.asyncio
    async def test_retrieve_with_stats(self):
        """Test retrieve_with_stats method."""

        class ConcreteRetriever(BaseRetriever):
            async def retrieve(self, query, config_id, top_k=None, filters=None):
                return [
                    RetrievedChunk(
                        content="Result",
                        score=0.9,
                        chunk_id="1",
                        document_id="d",
                        config_id=config_id,
                        source_type=SourceType.VECTOR,
                    )
                ]

        retriever = ConcreteRetriever()
        result = await retriever.retrieve_with_stats("test", "config-123")

        assert isinstance(result, RetrievalResult)
        assert result.total_found == 1
        assert result.retrieval_time_ms > 0
        assert result.source_counts["vector"] == 1
