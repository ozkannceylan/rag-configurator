"""Pytest fixtures for E2E tests."""

import asyncio
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List

import httpx
import pytest
from pytest_asyncio import fixture

from helpers import make_config

BASE_URL = "http://localhost:8000"


def get_data(response: httpx.Response) -> Any:
    """Extract data from API response, supporting both envelope and direct formats.

    Handles two response formats:
    - Envelope: {"data": {...}, "success": true, ...}
    - Direct: {...} (the data itself)
    """
    resp = response.json()
    if isinstance(resp, dict):
        return resp.get("data", resp)
    return resp


def get_id(data: dict) -> str:
    """Extract ID from response data, supporting both 'id' and '_id' field names."""
    return data.get("id") or data.get("_id")


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
        data = get_data(response)
        access_token = data["access_token"]
    else:
        # User might already exist, try logging in
        response = await client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        assert response.status_code == 200, f"Failed to login: {response.text}"
        data = get_data(response)
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

    config_data = make_config(
        name=f"E2E Test Config {timestamp}",
        description="Test configuration for E2E testing",
    )

    response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    assert response.status_code == 201, f"Failed to create config: {response.text}"

    config = get_data(response)
    config_id = get_id(config)

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

    config_data = make_config(
        name=f"E2E Test Config {timestamp}",
        description="Test configuration for E2E testing",
    )

    response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    assert response.status_code == 201, f"Failed to create config: {response.text}"

    config = get_data(response)
    config_id = get_id(config)

    yield config_id

    # Cleanup: delete config
    try:
        await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
    except Exception:
        pass
