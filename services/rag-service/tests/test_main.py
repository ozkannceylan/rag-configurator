"""Tests for RAG service main application."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "rag-service"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_liveness_check(self, client):
        """Test liveness check endpoint."""
        response = await client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness_check(self, client, mock_mongodb):
        """Test readiness check endpoint."""
        mock_mongodb.command = AsyncMock(return_value={"ok": 1})

        response = await client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "mongodb" in data["checks"]


class TestRootEndpoints:
    """Tests for root endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "rag-service"
        assert "version" in data
        assert "api" in data

    @pytest.mark.asyncio
    async def test_api_v1_root(self, client):
        """Test API v1 root endpoint."""
        response = await client.get("/api/v1/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "RAG Service" in data["message"]
        assert "endpoints" in data


class TestProvidersEndpoint:
    """Tests for providers endpoint."""

    @pytest.mark.asyncio
    async def test_list_providers(self, client):
        """Test listing LLM providers."""
        response = await client.get("/api/v1/providers")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "default_provider" in data
        assert "default_model" in data

        # Should always have Ollama
        provider_ids = [p["id"] for p in data["providers"]]
        assert "ollama" in provider_ids

    @pytest.mark.asyncio
    async def test_providers_include_ollama(self, client):
        """Test that Ollama is always available."""
        response = await client.get("/api/v1/providers")

        data = response.json()
        ollama = next(
            (p for p in data["providers"] if p["id"] == "ollama"),
            None,
        )

        assert ollama is not None
        assert ollama["available"] is True
        assert "base_url" in ollama
