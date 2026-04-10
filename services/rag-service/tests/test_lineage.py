"""Tests for data lineage tracking endpoint."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.lineage import (
    QueryLineage,
    generate_query_id,
    store_query_lineage,
)
from app.retrieval.base import RetrievedChunk, SourceType


# ------------------------------------------------------------------
# Unit tests for lineage helpers
# ------------------------------------------------------------------


def test_generate_query_id():
    """Test query ID generation."""
    qid = generate_query_id()
    assert qid.startswith("q-")
    assert len(qid) == 14  # "q-" + 12 hex chars

    # Uniqueness
    qid2 = generate_query_id()
    assert qid != qid2


async def test_store_query_lineage():
    """Test storing lineage to MongoDB."""
    mock_collection = MagicMock()
    mock_collection.insert_one = AsyncMock()

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    sources = [
        RetrievedChunk(
            content="Paris is the capital of France.",
            score=0.95,
            chunk_id="chunk-1",
            document_id="doc-1",
            config_id="config-123",
            file_name="france.txt",
        ),
    ]

    query_id = await store_query_lineage(
        db=mock_db,
        query_id="q-test123",
        config_id="config-123",
        user_id="user-456",
        query="What is the capital of France?",
        answer="Paris is the capital of France.",
        sources=sources,
        steps=[],
        total_duration_ms=150.0,
        metadata={"agent_type": "naive"},
    )

    assert query_id == "q-test123"
    mock_collection.insert_one.assert_called_once()

    # Verify the document structure
    stored_doc = mock_collection.insert_one.call_args[0][0]
    assert stored_doc["query_id"] == "q-test123"
    assert stored_doc["config_id"] == "config-123"
    assert stored_doc["user_id"] == "user-456"
    assert len(stored_doc["chunks"]) == 1
    assert stored_doc["chunks"][0]["chunk_id"] == "chunk-1"
    assert stored_doc["chunks"][0]["source_file"]["file_name"] == "france.txt"


async def test_store_query_lineage_with_dicts():
    """Test storing lineage with dict sources (not RetrievedChunk)."""
    mock_collection = MagicMock()
    mock_collection.insert_one = AsyncMock()

    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    sources = [
        {
            "content": "Some content",
            "score": 0.8,
            "chunk_id": "c-1",
            "document_id": "d-1",
            "file_name": "test.pdf",
        }
    ]

    await store_query_lineage(
        db=mock_db,
        query_id="q-dict",
        config_id="cfg-1",
        user_id="u-1",
        query="query",
        answer="answer",
        sources=sources,
        steps=[],
        total_duration_ms=100.0,
    )

    stored_doc = mock_collection.insert_one.call_args[0][0]
    assert len(stored_doc["chunks"]) == 1
    assert stored_doc["chunks"][0]["content_preview"] == "Some content"


# ------------------------------------------------------------------
# API endpoint tests
# ------------------------------------------------------------------


async def test_get_lineage_endpoint(client, mock_mongodb):
    """Test GET /api/v1/lineage/{query_id}."""
    lineage_doc = {
        "query_id": "q-abc123",
        "config_id": "config-123",
        "user_id": "user-456",
        "query": "What is Python?",
        "answer_preview": "Python is a programming language.",
        "agent_type": "naive",
        "query_type": "",
        "chunks": [
            {
                "chunk_id": "c-1",
                "content_preview": "Python is...",
                "score": 0.9,
                "source_file": {
                    "file_name": "python.txt",
                    "file_path": "/data/python.txt",
                    "file_type": ".txt",
                    "document_id": "doc-1",
                },
                "chunk_index": 0,
                "used_in_generation": True,
            }
        ],
        "steps": [],
        "total_duration_ms": 200.0,
        "created_at": datetime.now(timezone.utc),
        "metadata": {},
    }

    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=lineage_doc)
    mock_mongodb.__getitem__ = MagicMock(return_value=mock_collection)

    response = await client.get("/api/v1/lineage/q-abc123")
    assert response.status_code == 200

    data = response.json()
    assert data["query_id"] == "q-abc123"
    assert data["config_id"] == "config-123"
    assert len(data["chunks"]) == 1
    assert data["chunks"][0]["source_file"]["file_name"] == "python.txt"


async def test_get_lineage_not_found(client, mock_mongodb):
    """Test GET lineage returns 404 for missing query."""
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=None)
    mock_mongodb.__getitem__ = MagicMock(return_value=mock_collection)

    response = await client.get("/api/v1/lineage/q-nonexistent")
    assert response.status_code == 404


async def test_get_lineage_wrong_user(client, mock_mongodb):
    """Test GET lineage returns 403 for wrong user."""
    lineage_doc = {
        "query_id": "q-other",
        "config_id": "config-123",
        "user_id": "other-user",
        "query": "test",
        "answer_preview": "test",
        "agent_type": "",
        "query_type": "",
        "chunks": [],
        "steps": [],
        "total_duration_ms": 0,
        "created_at": datetime.now(timezone.utc),
        "metadata": {},
    }

    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value=lineage_doc)
    mock_mongodb.__getitem__ = MagicMock(return_value=mock_collection)

    response = await client.get("/api/v1/lineage/q-other")
    assert response.status_code == 403


async def test_list_lineage_by_config(client, mock_mongodb):
    """Test GET /api/v1/lineage/config/{config_id}."""
    docs = [
        {
            "query_id": "q-1",
            "config_id": "config-123",
            "user_id": "user-456",
            "query": "Query 1",
            "answer_preview": "Answer 1",
            "agent_type": "naive",
            "query_type": "",
            "chunks": [],
            "steps": [],
            "total_duration_ms": 100,
            "created_at": datetime.now(timezone.utc),
            "metadata": {},
        },
    ]

    class AsyncCursorMock:
        def __init__(self, items):
            self._items = items
            self._index = 0

        def sort(self, *a, **kw):
            return self

        def skip(self, *a, **kw):
            return self

        def limit(self, *a, **kw):
            return self

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._index >= len(self._items):
                raise StopAsyncIteration
            item = self._items[self._index]
            self._index += 1
            return item

    mock_collection = MagicMock()
    mock_collection.find = MagicMock(return_value=AsyncCursorMock(docs))
    mock_mongodb.__getitem__ = MagicMock(return_value=mock_collection)

    response = await client.get("/api/v1/lineage/config/config-123")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["query_id"] == "q-1"
