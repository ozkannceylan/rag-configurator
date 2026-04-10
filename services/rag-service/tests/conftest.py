"""Pytest configuration and fixtures."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock
from rag_config_common.auth.hmac_verify import build_signed_headers


@pytest.fixture
def mock_mongodb():
    """Create a mock MongoDB database."""
    mock_db = MagicMock()
    mock_db.command = AsyncMock(return_value={"ok": 1})
    mock_db.__getitem__ = MagicMock(return_value=MagicMock())
    return mock_db


@pytest_asyncio.fixture
async def client(mock_mongodb):
    """Create a test client with mocked dependencies."""
    from app.main import app
    from app.core.settings import settings
    from app.db.mongodb import mongodb

    # Mock the database
    mongodb.database = mock_mongodb
    mongodb.client = MagicMock()

    async def sign_request(request):
        request.headers.setdefault("X-User-ID", "user-456")
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


@pytest_asyncio.fixture
async def unsigned_client(mock_mongodb):
    """Create a client that does not sign requests."""
    from app.main import app
    from app.db.mongodb import mongodb

    mongodb.database = mock_mongodb
    mongodb.client = MagicMock()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def sample_config():
    """Sample RAG configuration for testing."""
    return {
        "_id": "config-123",
        "name": "Test Config",
        "created_by": "user-456",
        "user_id": "user-456",
        "data_source": {
            "type": "local",
            "path": "/data/test",
        },
        "retrieval": {
            "top_k": 5,
            "min_score": 0.7,
        },
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
    }


@pytest.fixture
def sample_query():
    """Sample query for testing."""
    return {
        "query": "What is the capital of France?",
        "config_id": "config-123",
    }
