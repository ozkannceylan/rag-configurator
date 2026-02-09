"""E2E tests for configuration CRUD operations."""

from datetime import datetime

import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_create_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test creating a new configuration."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    config_data = {
        "name": f"Create Test Config {timestamp}",
        "description": "Test configuration creation",
        "data_source": {
            "type": "folder",
            "source": {
                "folder_path": "/test/data",
                "recursive": True,
            },
            "rbac": {
                "roles": ["admin"],
            },
        },
        "models": {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
            },
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "dimensions": 1536,
            },
        },
        "document_processing": {
            "data_types": ["text"],
            "chunking": {
                "strategy": "recursive",
                "chunk_size": 500,
            },
        },
        "retrieval": {
            "methods": ["vector"],
            "vector_search": {
                "top_k": 3,
            },
        },
        "agent": {
            "type": "naive",
            "max_iterations": 3,
        },
    }

    response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    assert response.status_code == 201
    data = response.json()["data"]

    assert data["name"] == config_data["name"]
    assert data["description"] == config_data["description"]
    assert "id" in data
    assert "created_at" in data

    # Cleanup
    await client.delete(f"/api/v1/configs/{data['id']}", headers=auth_headers)


@pytest.mark.asyncio
async def test_list_configs(client: httpx.AsyncClient, auth_headers: dict):
    """Test listing configurations."""
    # Create a test config first
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = {
        "name": f"List Test Config {timestamp}",
        "description": "Test config for listing",
        "data_source": {
            "type": "folder",
            "source": {"folder_path": "/test"},
        },
        "models": {
            "llm": {"provider": "openai", "model": "gpt-4o-mini"},
            "embedding": {"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536},
        },
        "document_processing": {"data_types": ["text"]},
        "retrieval": {"methods": ["vector"]},
        "agent": {"type": "naive"},
    }

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    config_id = create_response.json()["data"]["id"]

    # List configs
    response = await client.get("/api/v1/configs/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data

    # Our created config should be in the list
    config_names = [item["name"] for item in data["items"]]
    assert config_data["name"] in config_names

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)


@pytest.mark.asyncio
async def test_get_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test getting a specific configuration."""
    # Create a test config
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = {
        "name": f"Get Test Config {timestamp}",
        "description": "Test config for get operation",
        "data_source": {
            "type": "folder",
            "source": {"folder_path": "/test"},
        },
        "models": {
            "llm": {"provider": "openai", "model": "gpt-4o-mini"},
            "embedding": {"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536},
        },
        "document_processing": {"data_types": ["text"]},
        "retrieval": {"methods": ["vector"]},
        "agent": {"type": "naive"},
    }

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    config_id = create_response.json()["data"]["id"]

    # Get the config
    response = await client.get(f"/api/v1/configs/{config_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["id"] == config_id
    assert data["name"] == config_data["name"]
    assert data["description"] == config_data["description"]

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)


@pytest.mark.asyncio
async def test_update_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test updating a configuration."""
    # Create a test config
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = {
        "name": f"Update Test Config {timestamp}",
        "description": "Test config for update",
        "data_source": {
            "type": "folder",
            "source": {"folder_path": "/test"},
        },
        "models": {
            "llm": {"provider": "openai", "model": "gpt-4o-mini"},
            "embedding": {"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536},
        },
        "document_processing": {"data_types": ["text"]},
        "retrieval": {"methods": ["vector"]},
        "agent": {"type": "naive"},
    }

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    config_id = create_response.json()["data"]["id"]

    # Update the config
    update_data = {
        "name": f"Updated Config {timestamp}",
        "description": "Updated description",
    }

    response = await client.put(
        f"/api/v1/configs/{config_id}",
        headers=auth_headers,
        json=update_data,
    )
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)


@pytest.mark.asyncio
async def test_duplicate_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test duplicating a configuration."""
    # Create a test config
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = {
        "name": f"Duplicate Source Config {timestamp}",
        "description": "Source config for duplication",
        "data_source": {
            "type": "folder",
            "source": {"folder_path": "/test"},
        },
        "models": {
            "llm": {"provider": "openai", "model": "gpt-4o-mini"},
            "embedding": {"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536},
        },
        "document_processing": {"data_types": ["text"]},
        "retrieval": {"methods": ["vector"]},
        "agent": {"type": "naive"},
    }

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    config_id = create_response.json()["data"]["id"]

    # Duplicate the config
    new_name = f"Duplicated Config {timestamp}"
    response = await client.post(
        f"/api/v1/configs/{config_id}/duplicate",
        headers=auth_headers,
        params={"new_name": new_name},
    )
    assert response.status_code == 201
    data = response.json()["data"]

    assert data["name"] == new_name
    duplicated_id = data["id"]
    assert duplicated_id != config_id

    # Cleanup both configs
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
    await client.delete(f"/api/v1/configs/{duplicated_id}", headers=auth_headers)


@pytest.mark.asyncio
async def test_export_import_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test exporting and importing a configuration."""
    # Create a test config
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = {
        "name": f"Export Test Config {timestamp}",
        "description": "Config for export/import test",
        "data_source": {
            "type": "folder",
            "source": {"folder_path": "/test"},
        },
        "models": {
            "llm": {"provider": "openai", "model": "gpt-4o-mini"},
            "embedding": {"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536},
        },
        "document_processing": {"data_types": ["text"]},
        "retrieval": {"methods": ["vector"]},
        "agent": {"type": "naive"},
    }

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    config_id = create_response.json()["data"]["id"]

    # Export the config
    export_response = await client.get(
        f"/api/v1/configs/{config_id}/export",
        headers=auth_headers,
    )
    assert export_response.status_code == 200
    yaml_content = export_response.text
    assert "name:" in yaml_content
    assert config_data["name"] in yaml_content

    # Import the config
    import_response = await client.post(
        "/api/v1/configs/import",
        headers={**auth_headers, "Content-Type": "multipart/form-data"},
        files={"file": ("config.yaml", yaml_content, "application/x-yaml")},
    )
    assert import_response.status_code == 201
    imported_data = import_response.json()["data"]
    imported_id = imported_data["id"]
    assert imported_id != config_id

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
    await client.delete(f"/api/v1/configs/{imported_id}", headers=auth_headers)


@pytest.mark.asyncio
async def test_delete_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test deleting a configuration."""
    # Create a test config
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = {
        "name": f"Delete Test Config {timestamp}",
        "description": "Config to be deleted",
        "data_source": {
            "type": "folder",
            "source": {"folder_path": "/test"},
        },
        "models": {
            "llm": {"provider": "openai", "model": "gpt-4o-mini"},
            "embedding": {"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536},
        },
        "document_processing": {"data_types": ["text"]},
        "retrieval": {"methods": ["vector"]},
        "agent": {"type": "naive"},
    }

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    config_id = create_response.json()["data"]["id"]

    # Delete the config
    delete_response = await client.delete(
        f"/api/v1/configs/{config_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200
    assert "deleted" in delete_response.json()["data"]["message"].lower()

    # Verify it's deleted
    get_response = await client.get(f"/api/v1/configs/{config_id}", headers=auth_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_config_crud_full_flow(client: httpx.AsyncClient, auth_headers: dict):
    """Test complete config CRUD flow."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # 1. Create
    config_data = {
        "name": f"Full CRUD Config {timestamp}",
        "description": "Full CRUD test",
        "data_source": {
            "type": "folder",
            "source": {"folder_path": "/test"},
        },
        "models": {
            "llm": {"provider": "openai", "model": "gpt-4o-mini"},
            "embedding": {"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536},
        },
        "document_processing": {"data_types": ["text"]},
        "retrieval": {"methods": ["vector"]},
        "agent": {"type": "naive"},
    }

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    assert create_response.status_code == 201
    config_id = create_response.json()["data"]["id"]

    # 2. Get
    get_response = await client.get(f"/api/v1/configs/{config_id}", headers=auth_headers)
    assert get_response.status_code == 200

    # 3. List (verify our config is there)
    list_response = await client.get("/api/v1/configs/", headers=auth_headers)
    assert list_response.status_code == 200
    config_names = [item["name"] for item in list_response.json()["data"]["items"]]
    assert config_data["name"] in config_names

    # 4. Update
    update_response = await client.put(
        f"/api/v1/configs/{config_id}",
        headers=auth_headers,
        json={"description": "Updated description"},
    )
    assert update_response.status_code == 200

    # 5. Duplicate
    dup_response = await client.post(
        f"/api/v1/configs/{config_id}/duplicate",
        headers=auth_headers,
        params={"new_name": f"Duplicated {timestamp}"},
    )
    assert dup_response.status_code == 201
    dup_id = dup_response.json()["data"]["id"]

    # 6. Delete original
    del_response = await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
    assert del_response.status_code == 200

    # 7. Delete duplicate
    await client.delete(f"/api/v1/configs/{dup_id}", headers=auth_headers)
