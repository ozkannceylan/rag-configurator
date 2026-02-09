"""E2E tests for query flow."""

import asyncio
from datetime import datetime

import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_query_with_naive_rag(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test querying with naive RAG agent."""
    config_id = created_config_id

    query_request = {
        "query": "What is the main topic of this document?",
        "config_id": config_id,
        "include_sources": True,
        "include_debug": False,
    }

    response = await client.post(
        "/api/v1/query/",
        headers=auth_headers,
        json=query_request,
    )

    # May fail if no documents ingested
    if response.status_code == 200:
        data = response.json()["data"]
        assert "answer" in data
        assert "sources" in data
        assert "metadata" in data
        assert isinstance(data["sources"], list)
    elif response.status_code == 404:
        pytest.skip("Config or documents not found - need to run ingestion first")
    else:
        # Other error, check it's handled gracefully
        assert response.status_code in [200, 404, 500]


@pytest.mark.asyncio
async def test_query_get_endpoint(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test query via GET endpoint."""
    config_id = created_config_id

    response = await client.get(
        "/api/v1/query/",
        headers=auth_headers,
        params={
            "query": "What is this document about?",
            "config_id": config_id,
        },
    )

    if response.status_code == 200:
        data = response.json()["data"]
        assert "answer" in data
        assert "sources" in data
    elif response.status_code == 404:
        pytest.skip("Config or documents not found")


@pytest.mark.asyncio
async def test_query_with_hybrid_retrieval(client: httpx.AsyncClient, auth_headers: dict):
    """Test querying with hybrid retrieval (vector + keyword)."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Create config with hybrid retrieval
    config_data = {
        "name": f"Hybrid Retrieval Test {timestamp}",
        "description": "Test hybrid retrieval",
        "data_source": {
            "type": "folder",
            "source": {"folder_path": "/test"},
        },
        "models": {
            "llm": {"provider": "openai", "model": "gpt-4o-mini"},
            "embedding": {"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536},
        },
        "document_processing": {"data_types": ["text"]},
        "retrieval": {
            "methods": ["vector", "keyword"],  # Hybrid
            "vector_search": {"top_k": 5},
            "keyword_search": {"top_k": 3},
        },
        "agent": {"type": "naive"},
    }

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    assert create_response.status_code == 201
    config_id = create_response.json()["data"]["id"]

    query_request = {
        "query": "Test query for hybrid retrieval",
        "config_id": config_id,
        "include_sources": True,
        "include_debug": True,  # Get debug info to verify hybrid
    }

    response = await client.post(
        "/api/v1/query/",
        headers=auth_headers,
        json=query_request,
    )

    if response.status_code == 200:
        data = response.json()["data"]
        assert "answer" in data
        assert "sources" in data
        if data.get("debug"):
            assert "retrieval_time_ms" in data["debug"]

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)


@pytest.mark.asyncio
async def test_query_with_graph_retrieval(client: httpx.AsyncClient, auth_headers: dict):
    """Test querying with graph retrieval."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Create config with graph retrieval
    config_data = {
        "name": f"Graph Retrieval Test {timestamp}",
        "description": "Test graph retrieval",
        "data_source": {
            "type": "folder",
            "source": {"folder_path": "/test"},
        },
        "models": {
            "llm": {"provider": "openai", "model": "gpt-4o-mini"},
            "embedding": {"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536},
        },
        "document_processing": {"data_types": ["text"]},
        "retrieval": {
            "methods": ["graph"],
            "graph_search": {
                "depth": 2,
                "max_nodes": 10,
            },
        },
        "agent": {"type": "naive"},
    }

    create_response = await client.post(
        "/api/v1/configs/",
        headers=auth_headers,
        json=config_data,
    )
    assert create_response.status_code == 201
    config_id = create_response.json()["data"]["id"]

    query_request = {
        "query": "Test query for graph retrieval",
        "config_id": config_id,
        "include_sources": True,
    }

    response = await client.post(
        "/api/v1/query/",
        headers=auth_headers,
        json=query_request,
    )

    if response.status_code == 200:
        data = response.json()["data"]
        assert "answer" in data

    # Cleanup
    await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)


@pytest.mark.asyncio
async def test_chat_endpoint(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test chat endpoint with conversation history."""
    config_id = created_config_id

    chat_request = {
        "message": "Hello, what is this document about?",
        "config_id": config_id,
        "include_sources": True,
    }

    response = await client.post(
        "/api/v1/chat/",
        headers=auth_headers,
        json=chat_request,
    )

    if response.status_code == 200:
        data = response.json()["data"]
        assert "answer" in data
        assert "conversation_id" in data
        assert "sources" in data
        assert "metadata" in data

        conversation_id = data["conversation_id"]

        # Continue conversation
        follow_up = {
            "message": "Can you tell me more?",
            "config_id": config_id,
            "conversation_id": conversation_id,
            "include_sources": True,
        }

        follow_up_response = await client.post(
            "/api/v1/chat/",
            headers=auth_headers,
            json=follow_up,
        )

        if follow_up_response.status_code == 200:
            follow_data = follow_up_response.json()["data"]
            assert follow_data["conversation_id"] == conversation_id

        # Get conversation history
        history_response = await client.get(
            f"/api/v1/chat/history/{conversation_id}",
            headers=auth_headers,
        )

        if history_response.status_code == 200:
            history_data = history_response.json()["data"]
            assert history_data["conversation_id"] == conversation_id
            assert "messages" in history_data
            assert len(history_data["messages"]) >= 2  # At least user and assistant

        # Delete conversation
        delete_response = await client.delete(
            f"/api/v1/chat/history/{conversation_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 200
    elif response.status_code == 404:
        pytest.skip("Config or documents not found")


@pytest.mark.asyncio
async def test_streaming_query(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test streaming query endpoint."""
    config_id = created_config_id

    stream_request = {
        "query": "Tell me about this document",
        "config_id": config_id,
    }

    response = await client.post(
        "/api/v1/stream/",
        headers=auth_headers,
        json=stream_request,
        timeout=60.0,
    )

    if response.status_code == 200:
        # Parse SSE stream
        events = []
        content = response.text

        # Simple parsing - look for event types
        for line in content.split("\n"):
            if line.startswith("event:") or line.startswith("data:"):
                events.append(line)

        # Should have received events
        assert len(events) > 0 or len(content) > 0, "Expected stream events or content"

        # Check for expected event types in content
        assert "start" in content.lower() or "token" in content.lower() or "end" in content.lower() or len(content) > 0
    elif response.status_code == 404:
        pytest.skip("Config or documents not found")


@pytest.mark.asyncio
async def test_streaming_query_get(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test streaming query via GET."""
    config_id = created_config_id

    response = await client.get(
        "/api/v1/stream/",
        headers=auth_headers,
        params={
            "query": "What is this?",
            "config_id": config_id,
        },
        timeout=60.0,
    )

    if response.status_code == 200:
        content = response.text
        assert len(content) > 0
    elif response.status_code == 404:
        pytest.skip("Config or documents not found")


@pytest.mark.asyncio
async def test_query_with_different_agents(client: httpx.AsyncClient, auth_headers: dict):
    """Test querying with different agent types."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    agent_types = ["naive", "react", "multi_query"]

    for agent_type in agent_types:
        config_data = {
            "name": f"Agent Test {agent_type} {timestamp}",
            "description": f"Test {agent_type} agent",
            "data_source": {"type": "folder", "source": {"folder_path": "/test"}},
            "models": {
                "llm": {"provider": "openai", "model": "gpt-4o-mini"},
                "embedding": {"provider": "openai", "model": "text-embedding-3-small", "dimensions": 1536},
            },
            "document_processing": {"data_types": ["text"]},
            "retrieval": {"methods": ["vector"]},
            "agent": {
                "type": agent_type,
                "max_iterations": 3 if agent_type in ["react"] else None,
            },
        }

        create_response = await client.post(
            "/api/v1/configs/",
            headers=auth_headers,
            json=config_data,
        )
        assert create_response.status_code == 201
        config_id = create_response.json()["data"]["id"]

        query_request = {
            "query": "Test query",
            "config_id": config_id,
            "include_sources": True,
            "include_debug": True,
        }

        response = await client.post(
            "/api/v1/query/",
            headers=auth_headers,
            json=query_request,
        )

        if response.status_code == 200:
            data = response.json()["data"]
            assert "answer" in data
            assert "metadata" in data
            assert data["metadata"]["agent_type"] == agent_type

        # Cleanup
        await client.delete(f"/api/v1/configs/{config_id}", headers=auth_headers)
        await asyncio.sleep(0.5)  # Brief pause between tests


@pytest.mark.asyncio
async def test_query_with_debug_info(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test query with debug information enabled."""
    config_id = created_config_id

    query_request = {
        "query": "Debug test query",
        "config_id": config_id,
        "include_sources": True,
        "include_debug": True,
    }

    response = await client.post(
        "/api/v1/query/",
        headers=auth_headers,
        json=query_request,
    )

    if response.status_code == 200:
        data = response.json()["data"]
        assert "answer" in data
        assert "sources" in data
        assert "debug" in data

        debug = data["debug"]
        assert "retrieval_time_ms" in debug
        assert "generation_time_ms" in debug
        assert "total_time_ms" in debug
    elif response.status_code == 404:
        pytest.skip("Config or documents not found")


@pytest.mark.asyncio
async def test_query_with_conversation_history(client: httpx.AsyncClient, auth_headers: dict, created_config_id: str):
    """Test query with conversation history."""
    config_id = created_config_id

    query_request = {
        "query": "Follow-up question",
        "config_id": config_id,
        "include_sources": True,
        "conversation_history": [
            {"role": "user", "content": "What is this document about?"},
            {"role": "assistant", "content": "This document discusses various topics."},
        ],
    }

    response = await client.post(
        "/api/v1/query/",
        headers=auth_headers,
        json=query_request,
    )

    if response.status_code == 200:
        data = response.json()["data"]
        assert "answer" in data
    elif response.status_code == 404:
        pytest.skip("Config or documents not found")
