"""Tests for Phase 0 RAG API security hardening."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.base import LLMError


@pytest.mark.asyncio
async def test_query_rejects_non_owner(client, mock_mongodb):
    """Query endpoint should reject access to someone else's config."""
    mock_configs = MagicMock()
    mock_configs.find_one = AsyncMock(
        return_value={"_id": "config-123", "created_by": "other-user"}
    )
    mock_mongodb.__getitem__ = MagicMock(return_value=mock_configs)

    response = await client.post(
        "/api/v1/query/",
        json={"query": "hello", "config_id": "config-123"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_query_returns_503_on_llm_provider_failure(client, mock_mongodb):
    """Query endpoint should surface provider failures as 503."""
    mock_configs = MagicMock()
    mock_configs.find_one = AsyncMock(
        return_value={
            "_id": "config-123",
            "created_by": "user-456",
            "models": {
                "llm": {"provider": "openai", "model": "gpt-4o-mini"},
                "embedding": {"provider": "openai", "model": "text-embedding-3-small"},
            },
            "retrieval": {},
            "agent": {"template": "naive"},
            "prompts": {},
        }
    )
    mock_mongodb.__getitem__ = MagicMock(return_value=mock_configs)

    fake_agent = MagicMock()
    fake_agent.run = AsyncMock(
        side_effect=LLMError("upstream unavailable", provider="openai")
    )

    with patch("app.api.v1.query.get_retriever_from_config", return_value=MagicMock()), patch(
        "app.api.v1.query.get_llm_from_config", return_value=MagicMock()
    ), patch("app.api.v1.query.PromptManager", return_value=MagicMock()), patch(
        "app.api.v1.query.get_agent", return_value=fake_agent
    ):
        response = await client.post(
            "/api/v1/query/",
            json={"query": "hello", "config_id": "config-123"},
        )

    assert response.status_code == 503
    assert "LLM provider failure" in response.text


@pytest.mark.asyncio
async def test_stream_rejects_non_owner(client, mock_mongodb):
    """Streaming endpoint should reject access to someone else's config."""
    mock_configs = MagicMock()
    mock_configs.find_one = AsyncMock(
        return_value={"_id": "config-123", "created_by": "other-user"}
    )
    mock_mongodb.__getitem__ = MagicMock(return_value=mock_configs)

    response = await client.get(
        "/api/v1/stream/",
        params={"query": "hello", "config_id": "config-123"},
    )

    assert response.status_code == 403
