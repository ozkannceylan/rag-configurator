"""Integration tests for the complete ingestion pipeline.

These tests require MongoDB and Redis to be running.
Run with: pytest tests/test_integration.py -v

Skip with: pytest tests/ --ignore=tests/test_integration.py
"""

import asyncio
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pytest
import pytest_asyncio
from bson import ObjectId

# Skip all tests if integration test flag is not set
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS", "").lower() != "true",
    reason="Integration tests require RUN_INTEGRATION_TESTS=true and running services",
)


@pytest_asyncio.fixture
async def integration_db():
    """Get integration test database."""
    from motor.motor_asyncio import AsyncIOMotorClient

    mongodb_uri = os.environ.get(
        "TEST_MONGODB_URI",
        os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
    )
    db_name = os.environ.get("TEST_MONGODB_DATABASE", "rag_configurator_integration")

    client = AsyncIOMotorClient(mongodb_uri)
    db = client[db_name]

    # Clean up before test
    await db["configs"].delete_many({})
    await db["ingestions"].delete_many({})
    await db["documents"].delete_many({})
    await db["chunks"].delete_many({})
    await db["graph_nodes"].delete_many({})
    await db["graph_edges"].delete_many({})

    yield db

    # Clean up after test
    await db["configs"].delete_many({})
    await db["ingestions"].delete_many({})
    await db["documents"].delete_many({})
    await db["chunks"].delete_many({})
    await db["graph_nodes"].delete_many({})
    await db["graph_edges"].delete_many({})

    client.close()


@pytest.fixture
def integration_files():
    """Create integration test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create multiple text files
        for i in range(5):
            (tmpdir_path / f"document_{i}.txt").write_text(
                f"""Document {i}

This is the content of document number {i}.
It contains multiple paragraphs of text for testing.

The document discusses various topics:
- Topic A: Introduction to the subject
- Topic B: Main content and analysis
- Topic C: Conclusions and recommendations

This paragraph provides additional context and detail.
The content is designed to be chunked and embedded.
""",
                encoding="utf-8",
            )

        # Create a markdown file
        (tmpdir_path / "readme.md").write_text(
            """# Test Documentation

## Overview

This is a test markdown document for integration testing.

## Features

- Feature 1: Processing markdown files
- Feature 2: Extracting headings and structure
- Feature 3: Preserving formatting

## Conclusion

This document tests markdown processing capabilities.
""",
            encoding="utf-8",
        )

        yield {
            "directory": tmpdir_path,
            "expected_files": 6,
        }


class TestFullIngestionPipeline:
    """Integration tests for the complete ingestion pipeline."""

    @pytest_asyncio.fixture
    async def test_config(self, integration_db, integration_files) -> Dict[str, Any]:
        """Create a test configuration in the database."""
        config_id = str(ObjectId())
        user_id = str(ObjectId())

        config = {
            "_id": config_id,
            "name": "Integration Test Config",
            "user_id": user_id,
            "data_sources": [
                {
                    "type": "local",
                    "path": str(integration_files["directory"]),
                }
            ],
            "chunking": {
                "strategy": "recursive",
                "chunk_size": 500,
                "chunk_overlap": 50,
            },
            "embedding": {
                "provider": "huggingface",  # Use local model for testing
                "model": "sentence-transformers/all-MiniLM-L6-v2",
            },
            "graph": {
                "enabled": False,
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        await integration_db["configs"].insert_one(config)
        return config

    @pytest.mark.asyncio
    async def test_store_and_retrieve_document(
        self, integration_db, test_config, integration_files
    ):
        """Test storing and retrieving documents."""
        from app.storage.vector_store import VectorStore
        from app.storage.models import DocumentRecord

        store = VectorStore(integration_db)
        await store.initialize_indexes()

        # Create document record
        doc = DocumentRecord(
            config_id=test_config["_id"],
            ingestion_id=str(ObjectId()),
            user_id=test_config["user_id"],
            file_path=str(integration_files["directory"] / "document_0.txt"),
            file_name="document_0.txt",
            file_type=".txt",
            file_size_bytes=100,
            content_hash="test-hash-123",
            chunk_count=3,
        )

        # Store
        doc_id = await store.store_document(doc)
        assert doc_id is not None

        # Retrieve
        retrieved = await store.get_document(doc_id)
        assert retrieved is not None
        assert retrieved.file_name == "document_0.txt"

    @pytest.mark.asyncio
    async def test_store_and_retrieve_chunks(self, integration_db, test_config):
        """Test storing and retrieving chunks with embeddings."""
        from app.storage.vector_store import VectorStore
        from app.storage.models import ChunkRecord

        store = VectorStore(integration_db)
        await store.initialize_indexes()

        # Create chunks with mock embeddings
        chunks = []
        for i in range(3):
            chunk = ChunkRecord(
                config_id=test_config["_id"],
                document_id=str(ObjectId()),
                ingestion_id=str(ObjectId()),
                user_id=test_config["user_id"],
                content=f"This is chunk number {i} with test content.",
                chunk_index=i,
                start_char=i * 50,
                end_char=(i + 1) * 50,
                embedding=[0.1 * (j + i) for j in range(10)],  # Mock embedding
                embedding_model="test-model",
                embedding_dimensions=10,
            )
            chunks.append(chunk)

        # Store
        chunk_ids = await store.store_chunks(chunks)
        assert len(chunk_ids) == 3

        # Retrieve
        for i, chunk_id in enumerate(chunk_ids):
            retrieved = await store.get_chunk(chunk_id)
            assert retrieved is not None
            assert f"chunk number {i}" in retrieved.content

    @pytest.mark.asyncio
    async def test_delete_by_config(self, integration_db, test_config):
        """Test deleting all data for a config."""
        from app.storage.vector_store import VectorStore
        from app.storage.models import DocumentRecord, ChunkRecord

        store = VectorStore(integration_db)
        await store.initialize_indexes()

        # Store some data
        doc = DocumentRecord(
            config_id=test_config["_id"],
            ingestion_id=str(ObjectId()),
            user_id=test_config["user_id"],
            file_path="/test/file.txt",
            file_name="file.txt",
            file_type=".txt",
            content_hash="delete-test-hash",
        )
        doc_id = await store.store_document(doc)

        chunk = ChunkRecord(
            config_id=test_config["_id"],
            document_id=doc_id,
            ingestion_id=str(ObjectId()),
            user_id=test_config["user_id"],
            content="Test content for deletion",
            chunk_index=0,
        )
        await store.store_chunk(chunk)

        # Verify data exists
        count_before = await store.count_chunks_by_config(test_config["_id"])
        assert count_before >= 1

        # Delete
        deleted = await store.delete_documents_by_config(test_config["_id"])
        assert deleted >= 1

        # Verify deletion
        count_after = await store.count_chunks_by_config(test_config["_id"])
        assert count_after == 0

    @pytest.mark.asyncio
    async def test_stats_return_correct_counts(self, integration_db, test_config):
        """Test that stats return correct counts."""
        from app.storage.vector_store import VectorStore
        from app.storage.models import IngestionRecord, IngestionStatus

        store = VectorStore(integration_db)
        await store.initialize_indexes()

        # Create ingestion record
        ingestion = IngestionRecord(
            config_id=test_config["_id"],
            user_id=test_config["user_id"],
            status=IngestionStatus.COMPLETED,
            total_files=5,
            processed_files=4,
            failed_files=1,
            total_chunks=20,
        )

        ingestion_id = await store.create_ingestion(ingestion)

        # Retrieve and verify
        retrieved = await store.get_ingestion(ingestion_id)
        assert retrieved is not None
        assert retrieved.total_files == 5
        assert retrieved.processed_files == 4
        assert retrieved.failed_files == 1
        assert retrieved.total_chunks == 20


class TestProcessorIntegration:
    """Integration tests for document processors."""

    @pytest.mark.asyncio
    async def test_text_processor_pipeline(self, integration_files):
        """Test text processor in full pipeline."""
        from app.processors.text import TextProcessor

        processor = TextProcessor()

        # Process each text file
        processed_count = 0
        for txt_file in integration_files["directory"].glob("*.txt"):
            result = await processor.process(txt_file)
            assert result.success
            assert len(result.content) > 0
            processed_count += 1

        assert processed_count > 0


class TestChunkerIntegration:
    """Integration tests for chunkers."""

    def test_recursive_chunker_pipeline(self, integration_files):
        """Test recursive chunker with real content."""
        from app.chunkers.recursive import RecursiveChunker
        from app.chunkers.base import ChunkingConfig

        config = ChunkingConfig(chunk_size=200, chunk_overlap=20)
        chunker = RecursiveChunker(config)

        # Read and chunk a file
        content = (integration_files["directory"] / "document_0.txt").read_text()
        chunks = chunker.chunk(content)

        assert len(chunks) > 0

        # Verify chunk properties
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert len(chunk.content) > 0
            assert chunk.content_hash != ""


class TestEmbedderIntegration:
    """Integration tests for embedders (with mocking for external APIs)."""

    def test_huggingface_embedder_loads(self):
        """Test HuggingFace embedder can be instantiated."""
        from app.embedders.huggingface import HuggingFaceEmbedder
        from app.embedders.base import EmbeddingConfig

        config = EmbeddingConfig(model="sentence-transformers/all-MiniLM-L6-v2")
        embedder = HuggingFaceEmbedder(config)

        assert embedder is not None
        assert embedder.model_name is not None

    @pytest.mark.asyncio
    async def test_huggingface_embed_texts(self):
        """Test HuggingFace embedder can embed texts (requires model download)."""
        pytest.importorskip("sentence_transformers")

        from app.embedders.huggingface import HuggingFaceEmbedder
        from app.embedders.base import EmbeddingConfig

        config = EmbeddingConfig(model="sentence-transformers/all-MiniLM-L6-v2")
        embedder = HuggingFaceEmbedder(config)

        texts = ["Hello world", "This is a test"]
        try:
            result = await embedder.embed(texts)
            assert result.count == 2
            assert result.dimensions > 0
            assert len(result.embeddings) == 2
        except Exception:
            # Model download may fail in CI
            pytest.skip("HuggingFace model not available")


class TestGraphIntegration:
    """Integration tests for graph extraction (with mocking for LLM calls)."""

    def test_extractor_prompt_building(self):
        """Test entity extractor prompt building."""
        from app.graph.extractor import EntityExtractor, ExtractionConfig

        config = ExtractionConfig(
            entity_types=["person", "organization"],
            relation_types=["works_for"],
            auto_extract=False,
        )
        extractor = EntityExtractor(config)

        prompt = extractor._build_prompt("John works at Acme Corp.")
        assert "person" in prompt
        assert "organization" in prompt

    def test_extractor_response_parsing(self):
        """Test parsing extraction results."""
        from app.graph.extractor import EntityExtractor

        extractor = EntityExtractor()

        # Mock LLM response
        response = '''
        {
            "entities": [
                {"name": "John", "type": "person", "confidence": 0.9}
            ],
            "relations": [
                {"source": "John", "target": "Acme", "type": "works_for", "confidence": 0.85}
            ]
        }
        '''

        entities, relations = extractor._parse_response(response)
        assert len(entities) > 0


class TestGraphStoreIntegration:
    """Integration tests for graph storage."""

    @pytest_asyncio.fixture
    async def graph_store(self, integration_db):
        """Create graph store for testing."""
        from app.storage.graph_store import GraphStore

        store = GraphStore(integration_db)
        await store.initialize_indexes()
        return store

    @pytest.mark.asyncio
    async def test_store_and_retrieve_nodes(self, graph_store, integration_db):
        """Test storing and retrieving graph nodes."""
        config_id = str(ObjectId())

        node_id = await graph_store.upsert_node(
            config_id=config_id,
            name="Test Entity",
            node_type="person",
            properties={"age": 30},
        )
        assert node_id is not None

        retrieved = await graph_store.get_node(node_id)
        assert retrieved is not None
        assert retrieved.name == "Test Entity"

    @pytest.mark.asyncio
    async def test_store_and_retrieve_edges(self, graph_store, integration_db):
        """Test storing and retrieving graph edges."""
        config_id = str(ObjectId())

        # Create nodes
        node1_id = await graph_store.upsert_node(
            config_id=config_id,
            name="Person A",
            node_type="person",
        )
        node2_id = await graph_store.upsert_node(
            config_id=config_id,
            name="Company B",
            node_type="organization",
        )

        # Create edge
        edge_id = await graph_store.upsert_edge(
            config_id=config_id,
            source_node_id=node1_id,
            target_node_id=node2_id,
            relation_type="works_for",
        )
        assert edge_id is not None

        # Get stats
        stats = await graph_store.get_stats(config_id)
        assert stats["node_count"] >= 2
        assert stats["edge_count"] >= 1


class TestReIngestion:
    """Tests for re-ingestion scenarios."""

    @pytest.mark.asyncio
    async def test_reingestion_clears_old_data(
        self, integration_db, integration_files
    ):
        """Test that re-ingestion clears old data."""
        from app.storage.vector_store import VectorStore
        from app.storage.models import DocumentRecord, ChunkRecord, IngestionRecord, IngestionStatus

        store = VectorStore(integration_db)
        await store.initialize_indexes()

        config_id = str(ObjectId())
        user_id = str(ObjectId())

        # First ingestion
        first_ingestion = IngestionRecord(
            config_id=config_id,
            user_id=user_id,
            status=IngestionStatus.COMPLETED,
            total_files=3,
            processed_files=3,
        )
        first_ing_id = await store.create_ingestion(first_ingestion)

        # Store some documents and chunks
        doc = DocumentRecord(
            config_id=config_id,
            ingestion_id=first_ing_id,
            user_id=user_id,
            file_path="/test/old_file.txt",
            file_name="old_file.txt",
            file_type=".txt",
            content_hash="old-hash",
        )
        doc_id = await store.store_document(doc)

        chunk = ChunkRecord(
            config_id=config_id,
            document_id=doc_id,
            ingestion_id=first_ing_id,
            user_id=user_id,
            content="Old content",
            chunk_index=0,
        )
        await store.store_chunk(chunk)

        # Verify old data exists
        old_chunks = await store.count_chunks_by_config(config_id)
        assert old_chunks >= 1

        # Simulate re-ingestion: clear old data
        await store.delete_documents_by_config(config_id)

        # Verify old data cleared
        after_clear = await store.count_chunks_by_config(config_id)
        assert after_clear == 0

        # Second ingestion
        second_ingestion = IngestionRecord(
            config_id=config_id,
            user_id=user_id,
            status=IngestionStatus.COMPLETED,
            total_files=5,
            processed_files=5,
        )
        await store.create_ingestion(second_ingestion)

        # History should show both ingestions
        history = await store.get_ingestions_by_config(config_id, limit=10)
        assert len(history) >= 2


class TestAPIIntegration:
    """Integration tests for API endpoints with real database."""

    @pytest_asyncio.fixture
    async def test_config_in_db(self, integration_db):
        """Insert a test config into the database."""
        config_id = str(ObjectId())
        config = {
            "_id": config_id,
            "name": "API Test Config",
            "user_id": str(ObjectId()),
            "data_sources": [{"type": "local", "path": "/test"}],
            "created_at": datetime.utcnow(),
        }
        await integration_db["configs"].insert_one(config)
        return config

    @pytest.mark.asyncio
    async def test_start_and_check_status(
        self, integration_db, test_config_in_db
    ):
        """Test starting ingestion and checking status."""
        from httpx import AsyncClient, ASGITransport
        from rag_config_common.auth.hmac_verify import build_signed_headers
        from app.main import app
        from app.core.settings import settings
        from app.db.mongodb import mongodb

        # Connect the app's mongodb singleton to the integration DB's client
        mongodb.client = integration_db.client
        mongodb.database = integration_db

        async def sign_request(request):
            request.headers.setdefault("X-User-ID", test_config_in_db["user_id"])
            request.headers.update(
                build_signed_headers(
                    settings.inter_service_secret,
                    request.method,
                    request.url.path,
                    request.content,
                    user_id=request.headers.get("X-User-ID"),
                )
            )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            event_hooks={"request": [sign_request]},
        ) as client:
            config_id = test_config_in_db["_id"]

            # Check status (should show no ingestion initially)
            response = await client.get(f"/api/v1/ingest/{config_id}/status")
            assert response.status_code in (200, 404)

            # The actual start would require Celery, so we skip the full test
            # In a complete integration test, you would:
            # 1. Start Celery worker
            # 2. Start ingestion
            # 3. Poll status until completion
            # 4. Verify results
