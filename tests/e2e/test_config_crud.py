"""E2E tests for configuration CRUD operations."""

from datetime import datetime

import httpx
import pytest

from helpers import get_data, get_id, make_config

BASE_URL = "http://localhost:8000"


async def test_create_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test creating a new configuration."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    config_data = make_config(name=f"Create Test Config {timestamp}", description="Test configuration creation")

    response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    assert response.status_code == 201
    data = get_data(response)

    assert data["name"] == config_data["name"]
    assert data["description"] == config_data["description"]
    config_id = get_id(data)
    assert config_id is not None
    assert "created_at" in data

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)


async def test_list_configs(client: httpx.AsyncClient, auth_headers: dict):
    """Test listing configurations."""
    # Create a test config first
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = make_config(name=f"List Test Config {timestamp}", description="Test config for listing")

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    created = get_data(create_response)
    config_id = get_id(created)

    # List configs
    response = await client.get("/api/v1/configs/", headers=auth_headers)
    assert response.status_code == 200
    data = get_data(response)

    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data

    # Our created config should be in the list
    config_names = [item["name"] for item in data["items"]]
    assert config_data["name"] in config_names

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)


async def test_get_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test getting a specific configuration."""
    # Create a test config
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = make_config(name=f"Get Test Config {timestamp}", description="Test config for get operation")

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    created = get_data(create_response)
    config_id = get_id(created)

    # Get the config
    response = await client.get(f"/api/v1/configs/{config_id}", headers=auth_headers)
    assert response.status_code == 200
    data = get_data(response)

    assert get_id(data) == config_id
    assert data["name"] == config_data["name"]
    assert data["description"] == config_data["description"]

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)


async def test_update_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test updating a configuration."""
    # Create a test config
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = make_config(name=f"Update Test Config {timestamp}", description="Test config for update")

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    created = get_data(create_response)
    config_id = get_id(created)

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
    data = get_data(response)

    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)


async def test_duplicate_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test duplicating a configuration."""
    # Create a test config
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = make_config(name=f"Duplicate Source Config {timestamp}", description="Source config for duplication")

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    created = get_data(create_response)
    config_id = get_id(created)

    # Duplicate the config
    new_name = f"Duplicated Config {timestamp}"
    response = await client.post(
        f"/api/v1/configs/{config_id}/duplicate",
        headers=auth_headers,
        params={"new_name": new_name},
    )
    assert response.status_code == 201
    data = get_data(response)

    assert data["name"] == new_name
    duplicated_id = get_id(data)
    assert duplicated_id != config_id

    # Cleanup both configs
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
    await client.delete(f"/api/v1/configs/{duplicated_id}", headers=auth_headers)


async def test_export_import_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test exporting and importing a configuration."""
    # Create a test config
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = make_config(name=f"Export Test Config {timestamp}", description="Config for export/import test")

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    created = get_data(create_response)
    config_id = get_id(created)

    # Export the config
    export_response = await client.get(
        f"/api/v1/configs/{config_id}/export",
        headers=auth_headers,
    )
    assert export_response.status_code == 200
    yaml_content = export_response.text
    assert "name:" in yaml_content
    assert config_data["name"] in yaml_content

    # Change name in YAML to avoid 409 conflict with the original
    yaml_content = yaml_content.replace(config_data["name"], f"Imported {config_data['name']}")

    # Import the config (don't override Content-Type — httpx sets multipart boundary)
    import_headers = {k: v for k, v in auth_headers.items() if k.lower() != "content-type"}
    import_response = await client.post(
        "/api/v1/configs/import",
        headers=import_headers,
        files={"file": ("config.yaml", yaml_content, "application/x-yaml")},
    )
    assert import_response.status_code == 201
    imported_data = get_data(import_response)
    imported_id = get_id(imported_data)
    assert imported_id != config_id

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
    await client.delete(f"/api/v1/configs/{imported_id}", headers=auth_headers)


async def test_delete_config(client: httpx.AsyncClient, auth_headers: dict):
    """Test deleting a configuration."""
    # Create a test config
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    config_data = make_config(name=f"Delete Test Config {timestamp}", description="Config to be deleted")

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    created = get_data(create_response)
    config_id = get_id(created)

    # Delete the config
    delete_response = await client.delete(
        f"/api/v1/configs/{config_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200
    del_data = get_data(delete_response)
    assert "deleted" in del_data.get("message", "").lower() or "deleted" in str(del_data).lower()

    # Verify it's deleted
    get_response = await client.get(f"/api/v1/configs/{config_id}", headers=auth_headers)
    assert get_response.status_code == 404


async def test_config_crud_full_flow(client: httpx.AsyncClient, auth_headers: dict):
    """Test complete config CRUD flow."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # 1. Create
    config_data = make_config(name=f"Full CRUD Config {timestamp}", description="Full CRUD test")

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    assert create_response.status_code == 201
    created = get_data(create_response)
    config_id = get_id(created)

    # 2. Get
    get_response = await client.get(f"/api/v1/configs/{config_id}", headers=auth_headers)
    assert get_response.status_code == 200

    # 3. List (verify our config is there)
    list_response = await client.get("/api/v1/configs/", headers=auth_headers)
    assert list_response.status_code == 200
    list_data = get_data(list_response)
    config_names = [item["name"] for item in list_data["items"]]
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
    dup_data = get_data(dup_response)
    dup_id = get_id(dup_data)

    # 6. Delete original
    del_response = await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
    assert del_response.status_code == 200

    # 7. Delete duplicate
    await client.delete(f"/api/v1/configs/{dup_id}", headers=auth_headers)
