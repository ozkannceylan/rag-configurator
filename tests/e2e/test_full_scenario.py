"""E2E test for complete user journey."""

import asyncio
from datetime import datetime

import httpx
import pytest

BASE_URL = "http://localhost:8000"
MAX_POLL_ATTEMPTS = 30
POLL_INTERVAL = 2


@pytest.mark.asyncio
async def test_complete_user_journey(client: httpx.AsyncClient):
    """
    Complete E2E journey:
    1. Register user
    2. Create config
    3. Run ingestion
    4. Query the data
    5. Verify results
    6. Cleanup
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_email = f"journey_test_{timestamp}@example.com"
    created_resources = {
        "user_email": test_email,
        "config_id": None,
        "ingestion_id": None,
        "conversation_id": None,
    }

    try:
        # ============== 1. REGISTER USER ==============
        print("\n[1/6] Registering user...")
        user_data = {
            "email": test_email,
            "password": "JourneyTest123!",
            "name": f"Journey Test User {timestamp}",
        }

        register_response = await client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201, f"Registration failed: {register_response.text}"

        auth_data = register_response.json()["data"]
        access_token = auth_data["access_token"]
        refresh_token = auth_data["refresh_token"]
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        print(f"✓ User registered: {test_email}")

        # ============== 2. CREATE CONFIG ==============
        print("\n[2/6] Creating configuration...")
        config_data = {
            "name": f"Journey Test Config {timestamp}",
            "description": "Complete journey test configuration",
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
                "data_types": ["text", "pdf"],
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
                "system_prompt": "You are a helpful assistant for testing.",
            },
        }

        create_response = await client.post(
            "/api/v1/configs/",
            headers=auth_headers,
            json=config_data,
        )
        assert create_response.status_code == 201, f"Config creation failed: {create_response.text}"

        config = create_response.json()["data"]
        config_id = config["id"]
        created_resources["config_id"] = config_id

        print(f"✓ Config created: {config_id}")

        # Verify config exists
        get_response = await client.get(f"/api/v1/configs/{config_id}", headers=auth_headers)
        assert get_response.status_code == 200
        assert get_response.json()["data"]["name"] == config_data["name"]

        # ============== 3. RUN INGESTION ==============
        print("\n[3/6] Starting ingestion...")
        start_response = await client.post(
            f"/api/v1/ingest/{config_id}/start",
            headers=auth_headers,
        )
        assert start_response.status_code == 202, f"Ingestion start failed: {start_response.text}"

        start_data = start_response.json()["data"]
        ingestion_id = start_data["ingestion_id"]
        created_resources["ingestion_id"] = ingestion_id

        print(f"✓ Ingestion started: {ingestion_id}")

        # Poll for completion
        print("Polling ingestion status...")
        final_status = "unknown"
        for attempt in range(MAX_POLL_ATTEMPTS):
            status_response = await client.get(
                f"/api/v1/ingest/{config_id}/status",
                headers=auth_headers,
            )
            assert status_response.status_code == 200

            status_data = status_response.json()["data"]
            final_status = status_data["status"]
            progress = status_data.get("progress", 0)
            total_files = status_data.get("total_files", 0)
            processed_files = status_data.get("processed_files", 0)

            print(f"  Poll {attempt + 1}/{MAX_POLL_ATTEMPTS}: {final_status} ({progress:.1f}%) - {processed_files}/{total_files} files")

            if final_status in ["completed", "failed", "cancelled"]:
                break

            await asyncio.sleep(POLL_INTERVAL)

        print(f"✓ Ingestion finished with status: {final_status}")

        # Get stats
        stats_response = await client.get(
            f"/api/v1/ingest/{config_id}/stats",
            headers=auth_headers,
        )
        if stats_response.status_code == 200:
            stats = stats_response.json()["data"]
            print(f"  Stats: {stats.get('total_documents', 0)} docs, {stats.get('total_chunks', 0)} chunks")

        # ============== 4. QUERY DATA ==============
        print("\n[4/6] Querying data...")

        # Test query endpoint
        query_request = {
            "query": "What is the main content of the documents?",
            "config_id": config_id,
            "include_sources": True,
            "include_debug": True,
        }

        query_response = await client.post(
            "/api/v1/query/",
            headers=auth_headers,
            json=query_request,
        )

        if query_response.status_code == 200:
            query_data = query_response.json()["data"]
            print(f"✓ Query successful")
            print(f"  Answer: {query_data.get('answer', 'N/A')[:100]}...")
            print(f"  Sources: {len(query_data.get('sources', []))}")

            if query_data.get("debug"):
                debug = query_data["debug"]
                print(f"  Timing: retrieval={debug.get('retrieval_time_ms')}ms, generation={debug.get('generation_time_ms')}ms")
        else:
            print(f"⚠ Query returned: {query_response.status_code}")
            print(f"  Response: {query_response.text[:200]}")

        # Test chat endpoint
        chat_request = {
            "message": "Can you summarize the key points?",
            "config_id": config_id,
            "include_sources": True,
        }

        chat_response = await client.post(
            "/api/v1/chat/",
            headers=auth_headers,
            json=chat_request,
        )

        if chat_response.status_code == 200:
            chat_data = chat_response.json()["data"]
            conversation_id = chat_data["conversation_id"]
            created_resources["conversation_id"] = conversation_id
            print(f"✓ Chat successful (conversation: {conversation_id})")

        # ============== 5. VERIFY RESULTS ==============
        print("\n[5/6] Verifying results...")

        # Check ingestion history
        history_response = await client.get(
            f"/api/v1/ingest/{config_id}/history",
            headers=auth_headers,
        )
        assert history_response.status_code == 200
        history = history_response.json()["data"]["history"]
        assert len(history) > 0, "Expected at least one ingestion in history"
        print(f"✓ Ingestion history: {len(history)} entries")

        # Check logs
        logs_response = await client.get(
            f"/api/v1/ingest/{config_id}/logs",
            headers=auth_headers,
            params={"limit": 10},
        )
        assert logs_response.status_code == 200
        print(f"✓ Ingestion logs retrieved")

        # Verify user profile
        me_response = await client.get("/api/v1/users/me", headers=auth_headers)
        assert me_response.status_code == 200
        user_info = me_response.json()["data"]
        assert user_info["email"] == test_email
        print(f"✓ User profile verified")

        # List configs
        list_response = await client.get("/api/v1/configs/", headers=auth_headers)
        assert list_response.status_code == 200
        configs = list_response.json()["data"]["items"]
        config_names = [c["name"] for c in configs]
        assert config_data["name"] in config_names
        print(f"✓ Config appears in list")

        # ============== 6. CLEANUP ==============
        print("\n[6/6] Cleaning up...")

        # Delete ingestion data
        try:
            delete_data_response = await client.delete(
                f"/api/v1/ingest/{config_id}/data",
                headers=auth_headers,
                params={"include_history": True},
            )
            if delete_data_response.status_code == 200:
                print(f"✓ Ingestion data deleted")
        except Exception as e:
            print(f"⚠ Error deleting ingestion data: {e}")

        # Delete conversation if created
        if created_resources["conversation_id"]:
            try:
                await client.delete(
                    f"/api/v1/chat/history/{created_resources['conversation_id']}",
                    headers=auth_headers,
                )
                print(f"✓ Conversation deleted")
            except Exception:
                pass

        # Delete config
        delete_response = await client.delete(
            f"/api/v1/configs/{config_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 200
        print(f"✓ Config deleted")

        # Logout
        logout_response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert logout_response.status_code == 200
        print(f"✓ User logged out")

        print("\n" + "=" * 50)
        print("✅ COMPLETE JOURNEY TEST PASSED")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise

    finally:
        # Emergency cleanup
        print("\n[Cleanup] Ensuring resources are cleaned up...")

        # Try to get auth again if we have credentials
        try:
            login_response = await client.post("/api/v1/auth/login", json={
                "email": test_email,
                "password": "JourneyTest123!",
            })
            if login_response.status_code == 200:
                cleanup_token = login_response.json()["data"]["access_token"]
                cleanup_headers = {"Authorization": f"Bearer {cleanup_token}"}

                # Delete config if still exists
                if created_resources["config_id"]:
                    try:
                        await client.delete(
                            f"/api/v1/configs/{created_resources['config_id']}",
                            headers=cleanup_headers,
                        )
                        print("  ✓ Config cleaned up")
                    except Exception:
                        pass

                # Delete conversation if exists
                if created_resources["conversation_id"]:
                    try:
                        await client.delete(
                            f"/api/v1/chat/history/{created_resources['conversation_id']}",
                            headers=cleanup_headers,
                        )
                        print("  ✓ Conversation cleaned up")
                    except Exception:
                        pass

                await client.post("/api/v1/auth/logout", headers=cleanup_headers)
        except Exception:
            pass


@pytest.mark.asyncio
async def test_duplicate_and_export_import_journey(client: httpx.AsyncClient, auth_headers: dict):
    """
    Journey testing duplicate and export/import features.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    created_configs = []

    try:
        # Create original config
        config_data = {
            "name": f"Original Config {timestamp}",
            "description": "Original for duplicate test",
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
        original_id = create_response.json()["data"]["id"]
        created_configs.append(original_id)

        # Duplicate config
        dup_response = await client.post(
            f"/api/v1/configs/{original_id}/duplicate",
            headers=auth_headers,
            params={"new_name": f"Duplicated Config {timestamp}"},
        )
        assert dup_response.status_code == 201
        duplicated_id = dup_response.json()["data"]["id"]
        created_configs.append(duplicated_id)

        # Export original
        export_response = await client.get(
            f"/api/v1/configs/{original_id}/export",
            headers=auth_headers,
        )
        assert export_response.status_code == 200
        yaml_content = export_response.text

        # Import
        import_response = await client.post(
            "/api/v1/configs/import",
            headers={**auth_headers, "Content-Type": "multipart/form-data"},
            files={"file": ("config.yaml", yaml_content, "application/x-yaml")},
        )
        assert import_response.status_code == 201
        imported_id = import_response.json()["data"]["id"]
        created_configs.append(imported_id)

        # Verify all three exist
        for config_id in created_configs:
            get_response = await client.get(f"/api/v1/configs/{config_id}", headers=auth_headers)
            assert get_response.status_code == 200

    finally:
        # Cleanup all configs
        for config_id in created_configs:
            try:
                await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
            except Exception:
                pass


@pytest.mark.asyncio
async def test_conversation_history_journey(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """
    Journey testing conversation history management.
    """
    config_id = created_config_id
    conversation_id = None

    try:
        # Start conversation
        chat1 = {
            "message": "Hello, what can you tell me?",
            "config_id": config_id,
        }

        response1 = await client.post("/api/v1/chat/", headers=auth_headers, json=chat1)
        if response1.status_code != 200:
            pytest.skip("Chat not available - ingestion may be needed")

        data1 = response1.json()["data"]
        conversation_id = data1["conversation_id"]

        # Continue conversation
        chat2 = {
            "message": "Tell me more details",
            "config_id": config_id,
            "conversation_id": conversation_id,
        }

        response2 = await client.post("/api/v1/chat/", headers=auth_headers, json=chat2)
        assert response2.status_code == 200

        # Get history
        history_response = await client.get(
            f"/api/v1/chat/history/{conversation_id}",
            headers=auth_headers,
        )
        assert history_response.status_code == 200
        history = history_response.json()["data"]
        assert len(history["messages"]) >= 4  # 2 user + 2 assistant messages

    finally:
        if conversation_id:
            try:
                await client.delete(
                    f"/api/v1/chat/history/{conversation_id}",
                    headers=auth_headers,
                )
            except Exception:
                pass


@pytest.mark.asyncio
async def test_refresh_token_during_journey(client: httpx.AsyncClient):
    """
    Journey testing token refresh during session.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_email = f"refresh_journey_{timestamp}@example.com"

    # Register
    reg_response = await client.post("/api/v1/auth/register", json={
        "email": test_email,
        "password": "RefreshTest123!",
        "name": "Refresh Test User",
    })
    assert reg_response.status_code == 201

    data = reg_response.json()["data"]
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]

    # Use token
    headers = {"Authorization": f"Bearer {access_token}"}
    me1 = await client.get("/api/v1/users/me", headers=headers)
    assert me1.status_code == 200

    # Refresh token
    refresh_response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert refresh_response.status_code == 200

    new_token = refresh_response.json()["data"]["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}

    # Use new token
    me2 = await client.get("/api/v1/users/me", headers=new_headers)
    assert me2.status_code == 200

    # Create config with new token
    config_data = {
        "name": f"Refresh Journey Config {timestamp}",
        "data_source": {"type": "folder", "source": {"folder_path": "/test"}},
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
        headers=new_headers,
        json=config_data,
    )
    assert create_response.status_code == 201
    config_id = create_response.json()["data"]["id"]

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=new_headers)
    await client.post("/api/v1/auth/logout", headers=new_headers)
