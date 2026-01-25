"""Tests for vector storage layer."""

from datetime import datetime

import pytest

from app.storage.models import (
    ChunkRecord,
    DocumentRecord,
    IngestionRecord,
    IngestionStatus,
    SearchResult,
)


class TestDocumentRecord:
    """Tests for DocumentRecord model."""

    def test_create_document_record(self):
        """Test creating a document record."""
        doc = DocumentRecord(
            config_id="config-123",
            ingestion_id="ing-456",
            user_id="user-789",
            file_path="/path/to/file.pdf",
            file_name="file.pdf",
            file_type=".pdf",
            content_hash="abc123",
        )

        assert doc.config_id == "config-123"
        assert doc.file_name == "file.pdf"
        assert doc.content_hash == "abc123"

    def test_document_to_mongo(self):
        """Test conversion to MongoDB document."""
        doc = DocumentRecord(
            config_id="config-123",
            ingestion_id="ing-456",
            user_id="user-789",
            file_path="/path/to/file.pdf",
            file_name="file.pdf",
            file_type=".pdf",
            content_hash="abc123",
        )

        mongo_doc = doc.to_mongo()
        assert "config_id" in mongo_doc
        assert "file_path" in mongo_doc
        assert mongo_doc["file_name"] == "file.pdf"

    def test_document_timestamps(self):
        """Test document timestamps are set."""
        doc = DocumentRecord(
            config_id="config-123",
            ingestion_id="ing-456",
            user_id="user-789",
            file_path="/path/to/file.pdf",
            file_name="file.pdf",
            file_type=".pdf",
            content_hash="abc123",
        )

        assert doc.created_at is not None
        assert doc.updated_at is not None
        assert doc.processed_at is not None


class TestChunkRecord:
    """Tests for ChunkRecord model."""

    def test_create_chunk_record(self):
        """Test creating a chunk record."""
        chunk = ChunkRecord(
            config_id="config-123",
            document_id="doc-456",
            ingestion_id="ing-789",
            user_id="user-000",
            content="This is test content.",
            chunk_index=0,
        )

        assert chunk.config_id == "config-123"
        assert chunk.content == "This is test content."
        assert chunk.chunk_index == 0

    def test_chunk_with_embedding(self):
        """Test chunk with embedding."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        chunk = ChunkRecord(
            config_id="config-123",
            document_id="doc-456",
            ingestion_id="ing-789",
            user_id="user-000",
            content="Test content",
            embedding=embedding,
            embedding_model="text-embedding-3-small",
            embedding_dimensions=5,
        )

        assert chunk.embedding == embedding
        assert chunk.embedding_dimensions == 5

    def test_chunk_to_mongo(self):
        """Test conversion to MongoDB document."""
        chunk = ChunkRecord(
            config_id="config-123",
            document_id="doc-456",
            ingestion_id="ing-789",
            user_id="user-000",
            content="Test content",
            folder_path="/data/folder1",
        )

        mongo_doc = chunk.to_mongo()
        assert mongo_doc["config_id"] == "config-123"
        assert mongo_doc["folder_path"] == "/data/folder1"

    def test_chunk_rbac_metadata(self):
        """Test chunk RBAC metadata."""
        chunk = ChunkRecord(
            config_id="config-123",
            document_id="doc-456",
            ingestion_id="ing-789",
            user_id="user-000",
            content="Test content",
            folder_path="/secure/folder",
            access_tags=["admin", "manager"],
        )

        assert chunk.folder_path == "/secure/folder"
        assert "admin" in chunk.access_tags


class TestIngestionRecord:
    """Tests for IngestionRecord model."""

    def test_create_ingestion_record(self):
        """Test creating an ingestion record."""
        ingestion = IngestionRecord(
            config_id="config-123",
            user_id="user-456",
        )

        assert ingestion.config_id == "config-123"
        assert ingestion.status == IngestionStatus.PENDING

    def test_ingestion_progress(self):
        """Test ingestion progress calculation."""
        ingestion = IngestionRecord(
            config_id="config-123",
            user_id="user-456",
            total_files=10,
            processed_files=5,
        )

        assert ingestion.progress_percent == 50.0

    def test_ingestion_progress_zero_files(self):
        """Test progress with zero files."""
        ingestion = IngestionRecord(
            config_id="config-123",
            user_id="user-456",
            total_files=0,
        )

        assert ingestion.progress_percent == 0.0

    def test_ingestion_duration(self):
        """Test ingestion duration calculation."""
        ingestion = IngestionRecord(
            config_id="config-123",
            user_id="user-456",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            completed_at=datetime(2024, 1, 1, 12, 1, 30),
        )

        assert ingestion.duration_seconds == 90.0

    def test_ingestion_status_values(self):
        """Test all ingestion status values."""
        assert IngestionStatus.PENDING == "pending"
        assert IngestionStatus.RUNNING == "running"
        assert IngestionStatus.COMPLETED == "completed"
        assert IngestionStatus.FAILED == "failed"
        assert IngestionStatus.CANCELLED == "cancelled"


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_create_search_result(self):
        """Test creating a search result."""
        result = SearchResult(
            chunk_id="chunk-123",
            document_id="doc-456",
            config_id="config-789",
            content="Matching content here",
            score=0.95,
        )

        assert result.chunk_id == "chunk-123"
        assert result.score == 0.95

    def test_search_result_with_metadata(self):
        """Test search result with file info."""
        result = SearchResult(
            chunk_id="chunk-123",
            document_id="doc-456",
            config_id="config-789",
            content="Matching content",
            score=0.85,
            file_name="document.pdf",
            file_path="/path/to/document.pdf",
            chunk_index=3,
        )

        assert result.file_name == "document.pdf"
        assert result.chunk_index == 3


class TestVectorStoreHelpers:
    """Tests for VectorStore helper methods."""

    def test_cosine_similarity(self):
        """Test cosine similarity calculation."""
        from app.storage.vector_store import VectorStore

        # Create mock store (we just need the method)
        class MockDB:
            def __getitem__(self, key):
                return None

        store = VectorStore(MockDB())

        # Test identical vectors
        vec = [1.0, 0.0, 0.0]
        assert store._cosine_similarity(vec, vec) == 1.0

        # Test orthogonal vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        assert store._cosine_similarity(vec1, vec2) == 0.0

        # Test opposite vectors
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        assert store._cosine_similarity(vec1, vec2) == -1.0

    def test_cosine_similarity_different_lengths(self):
        """Test cosine similarity with different length vectors."""
        from app.storage.vector_store import VectorStore

        class MockDB:
            def __getitem__(self, key):
                return None

        store = VectorStore(MockDB())

        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0]
        assert store._cosine_similarity(vec1, vec2) == 0.0

    def test_cosine_similarity_zero_vector(self):
        """Test cosine similarity with zero vector."""
        from app.storage.vector_store import VectorStore

        class MockDB:
            def __getitem__(self, key):
                return None

        store = VectorStore(MockDB())

        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        assert store._cosine_similarity(vec1, vec2) == 0.0
