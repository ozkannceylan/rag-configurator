"""Tests for configuration endpoints."""

import pytest

from rag_config_common.models.enums import (
    DataSourceType,
    LLMProvider,
    EmbeddingProvider,
    RetrievalMethod,
    AgentTemplate,
)


@pytest.fixture
def sample_config():
    """Sample configuration data."""
    return {
        "name": "Test Config",
        "description": "A test configuration",
        "data_source": {
            "type": DataSourceType.LOCAL.value,
            "base_path": "/data/test",
            "folders": [],
            "has_multimodal": False,
        },
        "models": {
            "llm": {
                "provider": LLMProvider.OPENAI.value,
                "model_name": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2048,
                "is_multimodal": False,
            },
            "embedding": {
                "provider": EmbeddingProvider.OPENAI.value,
                "model_name": "text-embedding-3-small",
                "dimensions": 1536,
            },
            "document_processing": {
                "use_docling": False,
                "use_vision_llm": False,
                "ocr_enabled": True,
            },
        },
        "retrieval": {
            "method": RetrievalMethod.NAIVE.value,
            "vector": {
                "enabled": True,
                "top_k": 5,
                "score_threshold": 0.7,
            },
            "keyword": {"enabled": False},
            "graph": {"enabled": False},
        },
        "agent": {
            "template": AgentTemplate.NAIVE_RAG.value,
            "max_iterations": 5,
            "enable_judge": False,
        },
        "prompts": {
            "system_prompt": "You are a helpful assistant.",
            "rag_prompt_template": "Context: {context}\n\nQuestion: {query}\n\nAnswer:",
        },
    }


@pytest.mark.asyncio
async def test_create_config(client, auth_headers, sample_config):
    """Test creating a configuration."""
    response = await client.post(
        "/api/v1/configs/",
        json=sample_config,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_config["name"]
    assert "id" in data


@pytest.mark.asyncio
async def test_list_configs(client, auth_headers, sample_config):
    """Test listing configurations."""
    # Create a config first
    await client.post("/api/v1/configs/", json=sample_config, headers=auth_headers)

    # List configs
    response = await client.get("/api/v1/configs/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_config(client, auth_headers, sample_config):
    """Test getting a specific configuration."""
    # Create config
    create_response = await client.post(
        "/api/v1/configs/",
        json=sample_config,
        headers=auth_headers,
    )
    config_id = create_response.json()["id"]

    # Get config
    response = await client.get(f"/api/v1/configs/{config_id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["id"] == config_id


@pytest.mark.asyncio
async def test_update_config(client, auth_headers, sample_config):
    """Test updating a configuration."""
    # Create config
    create_response = await client.post(
        "/api/v1/configs/",
        json=sample_config,
        headers=auth_headers,
    )
    config_id = create_response.json()["id"]

    # Update config
    update_data = {"name": "Updated Config Name"}
    response = await client.put(
        f"/api/v1/configs/{config_id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Config Name"


@pytest.mark.asyncio
async def test_delete_config(client, auth_headers, sample_config):
    """Test deleting a configuration."""
    # Create config
    create_response = await client.post(
        "/api/v1/configs/",
        json=sample_config,
        headers=auth_headers,
    )
    config_id = create_response.json()["id"]

    # Delete config
    response = await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)

    assert response.status_code == 200

    # Verify deleted
    get_response = await client.get(
        f"/api/v1/configs/{config_id}", headers=auth_headers
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_config_crud_writes_audit_logs(client, auth_headers, sample_config, test_db):
    """Test config create/update/delete flows create audit log entries."""
    create_response = await client.post(
        "/api/v1/configs/",
        json=sample_config,
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    config_id = create_response.json()["id"]

    update_response = await client.put(
        f"/api/v1/configs/{config_id}",
        json={"name": "Audited Config"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200

    delete_response = await client.delete(
        f"/api/v1/configs/{config_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200

    actions = []
    async for entry in test_db["audit_logs"].find({"resource_type": "config"}).sort("created_at", 1):
        actions.append(entry["action"])

    assert actions == ["config.create", "config.update", "config.delete"]


@pytest.mark.asyncio
async def test_unauthorized_access(client, sample_config):
    """Test that endpoints require authentication."""
    response = await client.get("/api/v1/configs/")
    assert response.status_code == 401
