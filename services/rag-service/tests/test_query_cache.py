"""Tests for QueryCache."""

import hashlib
import json
from unittest.mock import AsyncMock, patch

import pytest
from rag_config_common.cache.query_cache import QueryCache


@pytest.fixture
def cache():
    """Create a QueryCache instance (not connected)."""
    return QueryCache(
        redis_url="redis://localhost:6379/0",
        default_ttl_seconds=300,
        key_prefix="test_qcache",
    )


@pytest.fixture
def connected_cache(cache):
    """Create a QueryCache with a mocked Redis client."""
    mock_client = AsyncMock()
    cache.client = mock_client
    return cache


class TestCacheKey:
    """Test cache key generation."""

    def test_cache_key_format(self, cache):
        query_hash = hashlib.sha256(b"test query").hexdigest()
        key = cache._cache_key("config-123", "test query")
        assert key == f"test_qcache:config-123:{query_hash}"

    def test_cache_key_different_queries_differ(self, cache):
        key1 = cache._cache_key("config-1", "query a")
        key2 = cache._cache_key("config-1", "query b")
        assert key1 != key2

    def test_cache_key_different_configs_differ(self, cache):
        key1 = cache._cache_key("config-1", "query")
        key2 = cache._cache_key("config-2", "query")
        assert key1 != key2


class TestGet:
    """Test get operation."""

    async def test_get_returns_none_when_not_connected(self, cache):
        result = await cache.get("config-1", "query")
        assert result is None

    async def test_get_returns_response_on_hit(self, connected_cache):
        response = {"answer": "Paris", "sources": []}
        connected_cache.client.get = AsyncMock(return_value=json.dumps(response))

        result = await connected_cache.get("config-1", "query")
        assert result == response

    async def test_get_returns_none_on_miss(self, connected_cache):
        connected_cache.client.get = AsyncMock(return_value=None)

        result = await connected_cache.get("config-1", "query")
        assert result is None

    async def test_get_returns_none_on_redis_error(self, connected_cache):
        from redis.exceptions import RedisError

        connected_cache.client.get = AsyncMock(side_effect=RedisError("fail"))

        result = await connected_cache.get("config-1", "query")
        assert result is None

    async def test_get_returns_none_on_json_decode_error(self, connected_cache):
        connected_cache.client.get = AsyncMock(return_value="not-json{{{")

        result = await connected_cache.get("config-1", "query")
        assert result is None


class TestSet:
    """Test set operation."""

    async def test_set_noop_when_not_connected(self, cache):
        await cache.set("config-1", "query", {"answer": "test"})

    async def test_set_stores_response_with_default_ttl(self, connected_cache):
        response = {"answer": "Paris", "sources": []}
        await connected_cache.set("config-1", "query", response)

        connected_cache.client.set.assert_awaited_once()
        call_args = connected_cache.client.set.call_args
        assert "test_qcache:config-1:" in call_args[0][0]
        assert json.loads(call_args[0][1]) == response
        assert call_args[1]["ex"] == 300

    async def test_set_stores_response_with_custom_ttl(self, connected_cache):
        response = {"answer": "test"}
        await connected_cache.set("config-1", "query", response, ttl_seconds=600)

        call_args = connected_cache.client.set.call_args
        assert call_args[1]["ex"] == 600

    async def test_set_handles_redis_error(self, connected_cache):
        from redis.exceptions import RedisError

        connected_cache.client.set = AsyncMock(side_effect=RedisError("fail"))

        # Should not raise
        await connected_cache.set("config-1", "query", {"answer": "test"})


class TestInvalidateConfig:
    """Test config invalidation."""

    async def test_invalidate_noop_when_not_connected(self, cache):
        await cache.invalidate_config("config-1")

    async def test_invalidate_deletes_matching_keys(self, connected_cache):
        # Simulate SCAN returning keys, then cursor=0
        connected_cache.client.scan = AsyncMock(
            return_value=(0, ["test_qcache:config-1:abc", "test_qcache:config-1:def"])
        )
        connected_cache.client.delete = AsyncMock()

        await connected_cache.invalidate_config("config-1")

        connected_cache.client.scan.assert_awaited_once()
        connected_cache.client.delete.assert_awaited_once_with(
            "test_qcache:config-1:abc", "test_qcache:config-1:def"
        )

    async def test_invalidate_handles_no_keys(self, connected_cache):
        connected_cache.client.scan = AsyncMock(return_value=(0, []))

        await connected_cache.invalidate_config("config-1")
        connected_cache.client.delete.assert_not_awaited()

    async def test_invalidate_handles_redis_error(self, connected_cache):
        from redis.exceptions import RedisError

        connected_cache.client.scan = AsyncMock(side_effect=RedisError("fail"))

        # Should not raise
        await connected_cache.invalidate_config("config-1")


class TestConnect:
    """Test connect/disconnect."""

    async def test_connect_with_empty_url(self):
        cache = QueryCache(redis_url="")
        await cache.connect()
        assert cache.client is None

    async def test_disconnect_when_not_connected(self, cache):
        await cache.disconnect()
        assert cache.client is None

    async def test_disconnect_closes_client(self, connected_cache):
        await connected_cache.disconnect()
        assert connected_cache.client is None

    @patch("rag_config_common.cache.query_cache.REDIS_AVAILABLE", False)
    async def test_connect_without_redis_package(self):
        cache = QueryCache(redis_url="redis://localhost:6379/0")
        await cache.connect()
        assert cache.client is None


class TestGracefulDegradation:
    """Test graceful degradation when Redis is unavailable."""

    async def test_all_operations_noop_when_disconnected(self, cache):
        """All operations should silently no-op when not connected."""
        assert await cache.get("c", "q") is None
        await cache.set("c", "q", {"answer": "test"})
        await cache.invalidate_config("c")
