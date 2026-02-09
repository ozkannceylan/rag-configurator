"""Pytest fixtures for E2E tests."""

import asyncio
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List

import httpx
import pytest
from pytest_asyncio import fixture

BASE_URL = "http://localhost:8000"


@fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async HTTP client for API calls."""
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=60.0,
        follow_redirects=True,
    ) as client:
        yield client


@fixture
async def auth_headers(client: httpx.AsyncClient) -> Dict[str, str]:
    """Create test user, login, and return auth headers."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_user = {
        "email": f"e2e_test_{timestamp}@example.com",
        "password": "TestPassword123!",
        "name": f"E2E Test User {timestamp}",
    }

    # Register user
    response = await client.post("/api/v1/auth/register", json=test_user)
    if response.status_code == 201:
        data = response.json()["data"]
        access_token = data["access_token"]
    else:
        # User might already exist, try logging in
        response = await client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        assert response.status_code == 200, f"Failed to login: {response.text}"
        data = response.json()["data"]
        access_token = data["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    yield headers

    # Cleanup: logout
    try:
        await client.post("/api/v1/auth/logout", headers=headers)
    except Exception:
        pass


@fixture
async def sample_config(client: httpx.AsyncClient, auth_headers: Dict[str, str]) -> Dict[str, Any]:
    """Create a sample RAG configuration for testing."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    config_data = {
        "name": f"E2E Test Config {timestamp}",
        "description": "Test configuration for E2E testing",
        "data_source": {
            "type": "folder",
            "source": {
                "folder_path": "/test/data",
                "recursive": True,
            },
            "rbac": {
                "roles": ["admin", "user"],
            },
        },
        "models": {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2048,
            },
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "dimensions": 1536,
            },
        },
        "document_processing": {
            "data_types": ["text", "pdf", "docx"],
            "chunking": {
                "strategy": "recursive",
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
        },
        "retrieval": {
            "methods": ["vector", "keyword"],
            "vector_search": {
                "top_k": 5,
            },
            "keyword_search": {
                "top_k": 3,
            },
        },
        "agent": {
            "type": "naive",
            "max_iterations": 3,
        },
        "prompts": {
            "system_prompt": "You are a helpful assistant.",
        },
    }

    response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    assert response.status_code == 201, f"Failed to create config: {response.text}"

    config = response.json()["data"]
    config_id = config["id"]

    yield config

    # Cleanup: delete config
    try:
        await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
    except Exception:
        pass


@fixture
async def created_config_id(client: httpx.AsyncClient, auth_headers: Dict[str, str]) -> str:
    """Create a config and return just the ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    config_data = {
        "name": f"E2E Test Config {timestamp}",
        "description": "Test configuration for E2E testing",
        "data_source": {
            "type": "folder",
            "source": {
                "folder_path": "/test/data",
                "recursive": True,
            },
            "rbac": {
                "roles": ["admin", "user"],
            },
        },
        "models": {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2048,
            },
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "dimensions": 1536,
            },
        },
        "document_processing": {
            "data_types": ["text", "pdf", "docx"],
            "chunking": {
                "strategy": "recursive",
                "chunk_size": 1000,
                "chunk_overlap": 200,
            },
        },
        "retrieval": {
            "methods": ["vector", "keyword"],
            "vector_search": {
                "top_k": 5,
            },
            "keyword_search": {
                "top_k": 3,
            },
        },
        "agent": {
            "type": "naive",
            "max_iterations": 3,
        },
        "prompts": {
            "system_prompt": "You are a helpful assistant.",
        },
    }

    response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    assert response.status_code == 201, f"Failed to create config: {response.text}"

    config_id = response.json()["data"]["id"]

    yield config_id

    # Cleanup: delete config
    try:
        await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
    except Exception:
        pass
