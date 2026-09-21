"""Pytest configuration and fixtures."""

import asyncio
import os
import shutil
import tempfile
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from bson import ObjectId
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from rag_config_common.auth.hmac_verify import build_signed_headers

from app.core.settings import settings
from app.db.mongodb import mongodb
from app.main import app
from app.storage.models import (
    ChunkRecord,
    DocumentRecord,
    IngestionRecord,
    IngestionStatus,
)


class SignedTestClient:
    """Thin wrapper that signs each API request like the gateway."""

    def __init__(self, client: TestClient, *, secret: str, user_id: str | None = None):
        self._client = client
        self._secret = secret
        self._user_id = user_id

    def request(self, method: str, url: str, **kwargs):
        request = self._client.build_request(method, url, **kwargs)
        if self._user_id and "X-User-ID" not in request.headers:
            request.headers["X-User-ID"] = self._user_id
        request.headers.update(
            build_signed_headers(
                self._secret,
                request.method,
                request.url.path,
                request.content,
                user_id=request.headers.get("X-User-ID"),
            )
        )
        return self._client.send(request)

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)

    def options(self, url: str, **kwargs):
        return self.request("OPTIONS", url, **kwargs)

    def __getattr__(self, item):
        return getattr(self._client, item)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client(mock_mongodb: MagicMock) -> Generator[TestClient, None, None]:
    """Create synchronous test client."""
    original_database = mongodb.database
    mongodb.database = mock_mongodb

    with (
        patch.object(mongodb, "connect", AsyncMock()),
        patch.object(mongodb, "disconnect", AsyncMock()),
    ):
        with TestClient(app) as c:
            yield SignedTestClient(
                c,
                secret=settings.inter_service_secret,
                user_id="test-user-id",
            )

    mongodb.database = original_database


@pytest_asyncio.fixture
async def async_client(mock_mongodb: MagicMock) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    original_database = mongodb.database
    mongodb.database = mock_mongodb

    async def sign_request(request):
        request.headers.setdefault("X-User-ID", "test-user-id")
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
    ) as ac:
        yield ac

    mongodb.database = original_database


@pytest_asyncio.fixture
async def signed_client_without_user(
    mock_mongodb: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async client that signs requests but omits X-User-ID."""
    original_database = mongodb.database
    mongodb.database = mock_mongodb

    async def sign_request(request):
        request.headers.update(
            build_signed_headers(
                settings.inter_service_secret,
                request.method,
                request.url.path,
                request.content,
            )
        )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        event_hooks={"request": [sign_request]},
    ) as ac:
        yield ac

    mongodb.database = original_database


@pytest.fixture(scope="session", autouse=True)
def sandbox_tempdir() -> Generator[Path, None, None]:
    """Force tempfile usage into the writable workspace."""
    temp_root = Path(__file__).resolve().parent.parent / ".tmp-tests"
    temp_root.mkdir(exist_ok=True)

    original_tempdir = tempfile.tempdir
    original_tmp = os.environ.get("TMP")
    original_temp = os.environ.get("TEMP")

    tempfile.tempdir = str(temp_root)
    os.environ["TMP"] = str(temp_root)
    os.environ["TEMP"] = str(temp_root)

    yield temp_root

    tempfile.tempdir = original_tempdir
    if original_tmp is None:
        os.environ.pop("TMP", None)
    else:
        os.environ["TMP"] = original_tmp
    if original_temp is None:
        os.environ.pop("TEMP", None)
    else:
        os.environ["TEMP"] = original_temp


@pytest.fixture
def workspace_temp_directory(sandbox_tempdir: Path) -> Generator[Path, None, None]:
    """Create a writable temporary directory within the workspace."""
    path = sandbox_tempdir / f"case-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    yield path
    shutil.rmtree(path, ignore_errors=True)


# ==================== Sample Data Fixtures ====================


@pytest.fixture
def sample_config_id() -> str:
    """Return a sample config ID."""
    return str(ObjectId())


@pytest.fixture
def sample_user_id() -> str:
    """Return a sample user ID."""
    return "test-user-id"


@pytest.fixture
def sample_config(sample_config_id: str, sample_user_id: str) -> dict[str, Any]:
    """Return a sample configuration."""
    return {
        "_id": sample_config_id,
        "name": "Test Config",
        "created_by": sample_user_id,
        "user_id": sample_user_id,
        "data_sources": [
            {
                "type": "local",
                "path": "/test/data",
            }
        ],
        "chunking": {
            "strategy": "recursive",
            "chunk_size": 1000,
            "chunk_overlap": 200,
        },
        "embedding": {
            "provider": "openai",
            "model": "text-embedding-3-small",
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_ingestion_record(
    sample_config_id: str, sample_user_id: str
) -> IngestionRecord:
    """Return a sample ingestion record."""
    return IngestionRecord(
        id=str(ObjectId()),
        config_id=sample_config_id,
        user_id=sample_user_id,
        status=IngestionStatus.PENDING,
        total_files=10,
        processed_files=0,
        failed_files=0,
        total_chunks=0,
    )


@pytest.fixture
def sample_document_record(
    sample_config_id: str, sample_user_id: str
) -> DocumentRecord:
    """Return a sample document record."""
    return DocumentRecord(
        id=str(ObjectId()),
        config_id=sample_config_id,
        ingestion_id=str(ObjectId()),
        user_id=sample_user_id,
        file_path="/test/data/test.txt",
        file_name="test.txt",
        file_type=".txt",
        file_size_bytes=1024,
        content_hash="abc123",
        chunk_count=5,
    )


@pytest.fixture
def sample_chunk_record(sample_config_id: str, sample_user_id: str) -> ChunkRecord:
    """Return a sample chunk record."""
    return ChunkRecord(
        id=str(ObjectId()),
        config_id=sample_config_id,
        document_id=str(ObjectId()),
        ingestion_id=str(ObjectId()),
        user_id=sample_user_id,
        content="This is test content for chunking.",
        chunk_index=0,
        start_char=0,
        end_char=36,
    )


# ==================== File Fixtures ====================


@pytest.fixture
def temp_text_file() -> Generator[Path, None, None]:
    """Create a temporary text file for testing."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write("""This is a test document.
It has multiple lines of content.
The content is used for testing document processing.
This paragraph has more text to ensure chunking works properly.

Here is a second paragraph with additional content.
It provides more text for the chunker to work with.
""")
        path = Path(f.name)

    yield path

    # Cleanup
    if path.exists():
        path.unlink()


@pytest.fixture
def temp_markdown_file() -> Generator[Path, None, None]:
    """Create a temporary markdown file for testing."""
    content = """# Test Document

## Introduction

This is a test markdown document for testing processors.

## Content Section

Here is some content with **bold** and *italic* text.

### Subsection

- Item 1
- Item 2
- Item 3

## Conclusion

This concludes the test document.
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        path = Path(f.name)

    yield path

    # Cleanup
    if path.exists():
        path.unlink()


@pytest.fixture
def temp_directory(workspace_temp_directory: Path) -> Generator[Path, None, None]:
    """Create a temporary directory with sample files."""
    # Create text file
    (workspace_temp_directory / "file1.txt").write_text(
        "This is the first test file.", encoding="utf-8"
    )

    # Create markdown file
    (workspace_temp_directory / "file2.md").write_text(
        "# Markdown\n\nThis is a markdown file.", encoding="utf-8"
    )

    # Create subdirectory with file
    subdir = workspace_temp_directory / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text(
        "This is a file in a subdirectory.", encoding="utf-8"
    )

    yield workspace_temp_directory


# ==================== Mock Fixtures ====================


@pytest.fixture
def mock_mongodb() -> Generator[MagicMock, None, None]:
    """Create a mock MongoDB database."""
    mock_db = MagicMock()
    mock_db.command = AsyncMock(return_value={"ok": 1})
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    yield mock_db


@pytest.fixture
def mock_celery_task() -> MagicMock:
    """Create a mock Celery task."""
    task = MagicMock()
    task.id = "mock-task-id-12345"
    task.delay = MagicMock(return_value=task)
    return task


@pytest.fixture
def mock_vector_store() -> AsyncMock:
    """Create a mock VectorStore."""
    store = AsyncMock()
    store.create_ingestion = AsyncMock(return_value="mock-ingestion-id")
    store.get_ingestion = AsyncMock(return_value=None)
    store.get_ingestions_by_config = AsyncMock(return_value=[])
    store.update_ingestion_status = AsyncMock(return_value=True)
    store.store_document = AsyncMock(return_value="mock-doc-id")
    store.store_chunks = AsyncMock(return_value=["chunk-1", "chunk-2"])
    store.get_documents_by_config = AsyncMock(return_value=[])
    store.count_chunks_by_config = AsyncMock(return_value=0)
    return store


# ==================== Database Test Fixtures ====================


@pytest_asyncio.fixture
async def test_database() -> AsyncGenerator[Any, None]:
    """
    Create a test database connection.

    Uses a test database that is cleaned up after tests.
    Requires MongoDB to be running for integration tests.
    """
    from motor.motor_asyncio import AsyncIOMotorClient

    # Use test database
    test_uri = os.environ.get("TEST_MONGODB_URI", "mongodb://localhost:27017")
    test_db_name = os.environ.get("TEST_MONGODB_DATABASE", "rag_configurator_test")

    client = AsyncIOMotorClient(test_uri)
    db = client[test_db_name]

    yield db

    # Cleanup - drop test collections
    collections = [
        "configs",
        "ingestions",
        "documents",
        "chunks",
        "graph_nodes",
        "graph_edges",
    ]
    for collection in collections:
        await db[collection].delete_many({})

    client.close()


@pytest_asyncio.fixture
async def test_vector_store(test_database) -> AsyncGenerator[Any, None]:
    """Create a VectorStore with test database."""
    from app.storage.vector_store import VectorStore

    store = VectorStore(test_database)
    await store.initialize_indexes()
    yield store


# ==================== Integration Test Fixtures ====================


@pytest.fixture
def integration_test_files(temp_directory: Path) -> dict[str, Any]:
    """Prepare files for integration testing."""
    return {
        "directory": temp_directory,
        "files": list(temp_directory.rglob("*")),
        "expected_file_count": 3,
    }
