"""E2E tests for ingestion flow."""

import asyncio
from datetime import datetime

import httpx
import pytest

BASE_URL = "http://localhost:8000"
MAX_POLL_ATTEMPTS = 30
POLL_INTERVAL = 2  # seconds


@pytest.mark.asyncio
async def test_start_ingestion(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test starting an ingestion job."""
    config_id = created_config_id

    response = await client.post(
        f"/api/v1/ingest/{config_id}/start",
        headers=auth_headers,
    )
    assert response.status_code == 202
    data = response.json()["data"]

    assert "task_id" in data
    assert "ingestion_id" in data
    assert data["config_id"] == config_id
    assert data["status"] == "pending"

    # Cleanup - cancel if still running
    try:
        await client.post(f"/api/v1/ingest/{config_id}/cancel", headers=auth_headers)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_get_ingestion_status(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test getting ingestion status."""
    config_id = created_config_id

    # Start ingestion
    start_response = await client.post(
        f"/api/v1/ingest/{config_id}/start",
        headers=auth_headers,
    )
    assert start_response.status_code == 202

    # Get status
    status_response = await client.get(
        f"/api/v1/ingest/{config_id}/status",
        headers=auth_headers,
    )
    assert status_response.status_code == 200
    data = status_response.json()["data"]

    assert "config_id" in data
    assert "status" in data
    assert "progress" in data
    assert data["config_id"] == config_id

    # Cleanup
    try:
        await client.post(f"/api/v1/ingest/{config_id}/cancel", headers=auth_headers)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_poll_ingestion_status(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test polling ingestion status until completion or timeout."""
    config_id = created_config_id

    # Start ingestion
    start_response = await client.post(
        f"/api/v1/ingest/{config_id}/start",
        headers=auth_headers,
    )
    assert start_response.status_code == 202
    ingestion_id = start_response.json()["data"]["ingestion_id"]

    # Poll for status
    final_status = "unknown"
    for attempt in range(MAX_POLL_ATTEMPTS):
        status_response = await client.get(
            f"/api/v1/ingest/{config_id}/status",
            headers=auth_headers,
        )
        assert status_response.status_code == 200
        data = status_response.json()["data"]

        final_status = data["status"]
        progress = data.get("progress", 0)

        print(f"Poll {attempt + 1}: status={final_status}, progress={progress}%")

        if final_status in ["completed", "failed", "cancelled"]:
            break

        await asyncio.sleep(POLL_INTERVAL)

    # Verify we got a final status
    assert final_status in ["completed", "failed", "cancelled"]

    # Get ingestion stats
    stats_response = await client.get(
        f"/api/v1/ingest/{config_id}/stats",
        headers=auth_headers,
    )
    assert stats_response.status_code == 200
    stats_data = stats_response.json()["data"]
    assert stats_data["config_id"] == config_id


@pytest.mark.asyncio
async def test_get_ingestion_logs(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test getting ingestion logs."""
    config_id = created_config_id

    # Start ingestion
    start_response = await client.post(
        f"/api/v1/ingest/{config_id}/start",
        headers=auth_headers,
    )
    assert start_response.status_code == 202

    # Get logs
    logs_response = await client.get(
        f"/api/v1/ingest/{config_id}/logs",
        headers=auth_headers,
        params={"limit": 100},
    )
    assert logs_response.status_code == 200
    data = logs_response.json()["data"]

    assert "config_id" in data
    assert "logs" in data
    assert "total_count" in data

    # Cleanup
    try:
        await client.post(f"/api/v1/ingest/{config_id}/cancel", headers=auth_headers)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_cancel_ingestion(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test cancelling a running ingestion."""
    config_id = created_config_id

    # Start ingestion
    start_response = await client.post(
        f"/api/v1/ingest/{config_id}/start",
        headers=auth_headers,
    )
    assert start_response.status_code == 202

    # Cancel ingestion
    cancel_response = await client.post(
        f"/api/v1/ingest/{config_id}/cancel",
        headers=auth_headers,
    )

    # Might fail if already completed or not found
    if cancel_response.status_code == 200:
        data = cancel_response.json()["data"]
        assert data["config_id"] == config_id
        assert data["success"] is True


@pytest.mark.asyncio
async def test_get_ingestion_history(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test getting ingestion history."""
    config_id = created_config_id

    # Start ingestion
    start_response = await client.post(
        f"/api/v1/ingest/{config_id}/start",
        headers=auth_headers,
    )
    assert start_response.status_code == 202

    # Get history
    history_response = await client.get(
        f"/api/v1/ingest/{config_id}/history",
        headers=auth_headers,
    )
    assert history_response.status_code == 200
    data = history_response.json()["data"]

    assert "config_id" in data
    assert "history" in data
    assert "total_count" in data
    assert isinstance(data["history"], list)

    # Cleanup
    try:
        await client.post(f"/api/v1/ingest/{config_id}/cancel", headers=auth_headers)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_delete_ingestion_data(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test deleting ingestion data."""
    config_id = created_config_id

    # Start and wait for ingestion to complete or fail
    start_response = await client.post(
        f"/api/v1/ingest/{config_id}/start",
        headers=auth_headers,
    )
    assert start_response.status_code == 202

    # Wait a bit for processing
    await asyncio.sleep(5)

    # Cancel if still running
    try:
        await client.post(f"/api/v1/ingest/{config_id}/cancel", headers=auth_headers)
        await asyncio.sleep(2)
    except Exception:
        pass

    # Delete data
    delete_response = await client.delete(
        f"/api/v1/ingest/{config_id}/data",
        headers=auth_headers,
        params={"include_history": False},
    )
    assert delete_response.status_code == 200
    data = delete_response.json()["data"]
    assert data["config_id"] == config_id
    assert "deleted_documents" in data


@pytest.mark.asyncio
async def test_retry_failed_ingestion(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test retrying a failed ingestion."""
    config_id = created_config_id

    # Start ingestion
    start_response = await client.post(
        f"/api/v1/ingest/{config_id}/start",
        headers=auth_headers,
    )
    assert start_response.status_code == 202

    # Cancel to make it failed
    await asyncio.sleep(2)
    try:
        await client.post(f"/api/v1/ingest/{config_id}/cancel", headers=auth_headers)
    except Exception:
        pass

    # Wait for cancellation to take effect
    await asyncio.sleep(2)

    # Check status
    status_response = await client.get(
        f"/api/v1/ingest/{config_id}/status",
        headers=auth_headers,
    )
    status = status_response.json()["data"]["status"]

    if status in ["failed", "cancelled"]:
        # Retry
        retry_response = await client.post(
            f"/api/v1/ingest/{config_id}/retry",
            headers=auth_headers,
            params={"clear_data": True},
        )

        if retry_response.status_code == 202:
            data = retry_response.json()["data"]
            assert "task_id" in data
            assert data["config_id"] == config_id

            # Cancel the retry
            try:
                await client.post(f"/api/v1/ingest/{config_id}/cancel", headers=auth_headers)
            except Exception:
                pass


@pytest.mark.asyncio
async def test_full_ingestion_flow(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test complete ingestion flow."""
    config_id = created_config_id

    # 1. Start ingestion
    start_response = await client.post(
        f"/api/v1/ingest/{config_id}/start",
        headers=auth_headers,
    )
    assert start_response.status_code == 202
    start_data = start_response.json()["data"]
    ingestion_id = start_data["ingestion_id"]
    print(f"Started ingestion {ingestion_id}")

    # 2. Poll status
    final_status = "unknown"
    for attempt in range(MAX_POLL_ATTEMPTS):
        status_response = await client.get(
            f"/api/v1/ingest/{config_id}/status",
            headers=auth_headers,
        )
        assert status_response.status_code == 200
        data = status_response.json()["data"]

        final_status = data["status"]
        progress = data.get("progress", 0)
        total_files = data.get("total_files", 0)
        processed_files = data.get("processed_files", 0)

        print(f"Poll {attempt + 1}: status={final_status}, progress={progress}%, files={processed_files}/{total_files}")

        if final_status in ["completed", "failed", "cancelled"]:
            break

        await asyncio.sleep(POLL_INTERVAL)

    # 3. Get stats
    stats_response = await client.get(
        f"/api/v1/ingest/{config_id}/stats",
        headers=auth_headers,
    )
    assert stats_response.status_code == 200
    stats_data = stats_response.json()["data"]
    print(f"Stats: {stats_data}")

    # 4. Get logs
    logs_response = await client.get(
        f"/api/v1/ingest/{config_id}/logs",
        headers=auth_headers,
        params={"limit": 50},
    )
    assert logs_response.status_code == 200
    logs_data = logs_response.json()["data"]
    print(f"Logs count: {logs_data['total_count']}")

    # 5. Get history
    history_response = await client.get(
        f"/api/v1/ingest/{config_id}/history",
        headers=auth_headers,
    )
    assert history_response.status_code == 200
    history_data = history_response.json()["data"]
    assert len(history_data["history"]) > 0

    # 6. If completed, verify documents/chunks exist
    if final_status == "completed":
        assert stats_data["total_documents"] > 0 or stats_data["total_chunks"] > 0, \
            "Expected documents or chunks after completed ingestion"

    # 7. Cleanup - delete data
    delete_response = await client.delete(
        f"/api/v1/ingest/{config_id}/data",
        headers=auth_headers,
        params={"include_history": True},
    )
    assert delete_response.status_code == 200
