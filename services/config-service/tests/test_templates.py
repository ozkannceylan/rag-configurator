"""Tests for template marketplace endpoints."""

import pytest
from rag_config_common.models.enums import (
    AgentTemplate,
    DataSourceType,
    EmbeddingProvider,
    LLMProvider,
    RetrievalMethod,
)


@pytest.fixture
def sample_config():
    """Sample configuration data for creating a template source."""
    return {
        "name": "Template Source Config",
        "description": "A config to use as a template source",
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


@pytest.fixture
def template_create_data():
    """Data for creating a template (config_id will be set in tests)."""
    return {
        "name": "Test Template",
        "description": "A test template for RAG pipelines",
        "category": "qa",
        "tags": ["test", "basic"],
    }


@pytest.mark.asyncio
async def test_create_template(
    client, auth_headers, sample_config, template_create_data
):
    """Test creating a template from a config."""
    # Create a config first
    config_response = await client.post(
        "/api/v1/configs/", json=sample_config, headers=auth_headers
    )
    assert config_response.status_code == 201
    config_id = config_response.json()["id"]

    # Create template from the config
    template_create_data["config_id"] = config_id
    response = await client.post(
        "/api/v1/templates/", json=template_create_data, headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Template"
    assert data["category"] == "qa"
    assert data["tags"] == ["test", "basic"]
    assert data["usage_count"] == 0
    assert "config_snapshot" in data
    assert "id" in data


@pytest.mark.asyncio
async def test_list_templates(
    client, auth_headers, sample_config, template_create_data
):
    """Test listing templates."""
    # Create a config and template
    config_response = await client.post(
        "/api/v1/configs/", json=sample_config, headers=auth_headers
    )
    config_id = config_response.json()["id"]
    template_create_data["config_id"] = config_id
    await client.post(
        "/api/v1/templates/", json=template_create_data, headers=auth_headers
    )

    # List templates
    response = await client.get("/api/v1/templates/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["name"] == "Test Template"


@pytest.mark.asyncio
async def test_list_templates_with_category_filter(
    client, auth_headers, sample_config, template_create_data
):
    """Test listing templates with category filter."""
    # Create two templates with different categories
    config_response = await client.post(
        "/api/v1/configs/", json=sample_config, headers=auth_headers
    )
    config_id = config_response.json()["id"]

    template_create_data["config_id"] = config_id
    template_create_data["category"] = "qa"
    await client.post(
        "/api/v1/templates/", json=template_create_data, headers=auth_headers
    )

    template_create_data["name"] = "Another Template"
    template_create_data["category"] = "search"
    await client.post(
        "/api/v1/templates/", json=template_create_data, headers=auth_headers
    )

    # Filter by category
    response = await client.get("/api/v1/templates/?category=qa", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert all(item["category"] == "qa" for item in data["items"])


@pytest.mark.asyncio
async def test_list_templates_with_search(
    client, auth_headers, sample_config, template_create_data
):
    """Test listing templates with search."""
    config_response = await client.post(
        "/api/v1/configs/", json=sample_config, headers=auth_headers
    )
    config_id = config_response.json()["id"]
    template_create_data["config_id"] = config_id
    await client.post(
        "/api/v1/templates/", json=template_create_data, headers=auth_headers
    )

    # Search by name
    response = await client.get("/api/v1/templates/?search=Test", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_template(client, auth_headers, sample_config, template_create_data):
    """Test getting a specific template."""
    # Create config and template
    config_response = await client.post(
        "/api/v1/configs/", json=sample_config, headers=auth_headers
    )
    config_id = config_response.json()["id"]
    template_create_data["config_id"] = config_id
    create_response = await client.post(
        "/api/v1/templates/", json=template_create_data, headers=auth_headers
    )
    template_id = create_response.json()["id"]

    # Get template
    response = await client.get(
        f"/api/v1/templates/{template_id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == template_id
    assert data["name"] == "Test Template"
    assert "config_snapshot" in data


@pytest.mark.asyncio
async def test_clone_template(
    client, auth_headers, sample_config, template_create_data
):
    """Test cloning a template as a new config."""
    # Create config and template
    config_response = await client.post(
        "/api/v1/configs/", json=sample_config, headers=auth_headers
    )
    config_id = config_response.json()["id"]
    template_create_data["config_id"] = config_id
    create_response = await client.post(
        "/api/v1/templates/", json=template_create_data, headers=auth_headers
    )
    template_id = create_response.json()["id"]

    # Clone template
    response = await client.post(
        f"/api/v1/templates/{template_id}/clone?new_name=Cloned%20Config",
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Cloned Config"
    assert "id" in data

    # Verify template usage count incremented
    template_response = await client.get(
        f"/api/v1/templates/{template_id}", headers=auth_headers
    )
    assert template_response.json()["usage_count"] == 1


@pytest.mark.asyncio
async def test_delete_template(
    client, auth_headers, sample_config, template_create_data
):
    """Test deleting a template."""
    # Create config and template
    config_response = await client.post(
        "/api/v1/configs/", json=sample_config, headers=auth_headers
    )
    config_id = config_response.json()["id"]
    template_create_data["config_id"] = config_id
    create_response = await client.post(
        "/api/v1/templates/", json=template_create_data, headers=auth_headers
    )
    template_id = create_response.json()["id"]

    # Delete template
    response = await client.delete(
        f"/api/v1/templates/{template_id}", headers=auth_headers
    )
    assert response.status_code == 200

    # Verify deleted
    get_response = await client.get(
        f"/api/v1/templates/{template_id}", headers=auth_headers
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_template(client, auth_headers):
    """Test getting a template that doesn't exist."""
    response = await client.get(
        "/api/v1/templates/000000000000000000000000", headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_template_access(client):
    """Test that template endpoints require authentication."""
    response = await client.get("/api/v1/templates/")
    assert response.status_code == 401
