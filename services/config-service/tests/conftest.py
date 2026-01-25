"""Pytest fixtures for Config Service tests."""

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure

from app.main import app
from app.db.mongodb import mongodb
from app.core.settings import settings

# Check if MongoDB is available for testing
MONGODB_AVAILABLE = False
MONGODB_SKIP_REASON = "MongoDB not available for testing"


def check_mongodb_available():
    """Check if MongoDB is available and accessible."""
    global MONGODB_AVAILABLE, MONGODB_SKIP_REASON
    try:
        from pymongo import MongoClient

        # Use a short timeout for the check
        client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=2000,
        )
        # Try to ping the server
        client.admin.command("ping")
        # Try to list databases (tests auth)
        client.list_database_names()
        client.close()
        MONGODB_AVAILABLE = True
    except ServerSelectionTimeoutError:
        MONGODB_SKIP_REASON = "MongoDB server not running"
    except OperationFailure as e:
        if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
            MONGODB_SKIP_REASON = "MongoDB requires authentication"
        else:
            MONGODB_SKIP_REASON = f"MongoDB operation failed: {e}"
    except Exception as e:
        MONGODB_SKIP_REASON = f"MongoDB connection error: {e}"


# Run the check at module load
check_mongodb_available()

# Create a marker for tests that require MongoDB
requires_mongodb = pytest.mark.skipif(
    not MONGODB_AVAILABLE,
    reason=MONGODB_SKIP_REASON,
)


@pytest_asyncio.fixture
async def test_db():
    """Create a test database connection."""
    if not MONGODB_AVAILABLE:
        pytest.skip(MONGODB_SKIP_REASON)

    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[f"{settings.MONGODB_DATABASE}_test"]

    # Clear test collections
    for collection in await db.list_collection_names():
        await db[collection].delete_many({})

    yield db

    # Cleanup
    for collection in await db.list_collection_names():
        await db[collection].delete_many({})

    client.close()


@pytest_asyncio.fixture
async def client(test_db):
    """Create test client with test database."""
    # Override the database
    mongodb.client = test_db.client
    original_db_name = settings.MONGODB_DATABASE
    settings.MONGODB_DATABASE = f"{original_db_name}_test"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Restore original settings
    settings.MONGODB_DATABASE = original_db_name


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User",
    }


@pytest_asyncio.fixture
async def auth_headers(client, test_user_data):
    """Get authentication headers for test user."""
    # Register user
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
