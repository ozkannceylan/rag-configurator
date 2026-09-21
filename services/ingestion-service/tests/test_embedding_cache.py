"""Tests for EmbeddingCache."""

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rag_config_common.cache.embedding_cache import EmbeddingCache


@pytest.fixture
def cache():
    """Create an EmbeddingCache instance (not connected)."""
    return EmbeddingCache(
        redis_url="redis://localhost:6379/0",
        ttl_seconds=3600,
        key_prefix="test_emb",
    )


@pytest.fixture
def connected_cache(cache):
    """Create an EmbeddingCache with a mocked Redis client."""
    mock_client = AsyncMock()
    cache.client = mock_client
    return cache


class TestCacheKey:
    """Test cache key generation."""

    def test_cache_key_format(self, cache):
        text_hash = hashlib.sha256(b"hello").hexdigest()
        key = cache._cache_key("hello", "text-embedding-3-small")
        assert key == f"test_emb:text-embedding-3-small:{text_hash}"

    def test_cache_key_different_texts_differ(self, cache):
        key1 = cache._cache_key("hello", "model")
        key2 = cache._cache_key("world", "model")
        assert key1 != key2

    def test_cache_key_different_models_differ(self, cache):
        key1 = cache._cache_key("hello", "model-a")
        key2 = cache._cache_key("hello", "model-b")
        assert key1 != key2


class TestGet:
    """Test single get operation."""

    async def test_get_returns_none_when_not_connected(self, cache):
        result = await cache.get("hello", "model")
        assert result is None

    async def test_get_returns_embedding_on_hit(self, connected_cache):
        embedding = [0.1, 0.2, 0.3]
        connected_cache.client.get = AsyncMock(return_value=json.dumps(embedding))

        result = await connected_cache.get("hello", "model")
        assert result == embedding

    async def test_get_returns_none_on_miss(self, connected_cache):
        connected_cache.client.get = AsyncMock(return_value=None)

        result = await connected_cache.get("hello", "model")
        assert result is None

    async def test_get_returns_none_on_redis_error(self, connected_cache):
        from redis.exceptions import RedisError

        connected_cache.client.get = AsyncMock(side_effect=RedisError("fail"))

        result = await connected_cache.get("hello", "model")
        assert result is None

    async def test_get_returns_none_on_json_decode_error(self, connected_cache):
        connected_cache.client.get = AsyncMock(return_value="not-json")

        result = await connected_cache.get("hello", "model")
        assert result is None


class TestSet:
    """Test single set operation."""

    async def test_set_noop_when_not_connected(self, cache):
        # Should not raise
        await cache.set("hello", "model", [0.1, 0.2])

    async def test_set_stores_embedding_with_ttl(self, connected_cache):
        embedding = [0.1, 0.2, 0.3]
        await connected_cache.set("hello", "model", embedding)

        connected_cache.client.set.assert_awaited_once()
        call_args = connected_cache.client.set.call_args
        key = call_args[0][0]
        value = call_args[0][1]
        assert "test_emb:model:" in key
        assert json.loads(value) == embedding
        assert call_args[1]["ex"] == 3600

    async def test_set_handles_redis_error(self, connected_cache):
        from redis.exceptions import RedisError

        connected_cache.client.set = AsyncMock(side_effect=RedisError("fail"))

        # Should not raise
        await connected_cache.set("hello", "model", [0.1])


class TestBatchGet:
    """Test batch get operation."""

    async def test_batch_get_returns_empty_when_not_connected(self, cache):
        result = await cache.get_batch(["a", "b"], "model")
        assert result == {}

    async def test_batch_get_returns_empty_for_empty_input(self, connected_cache):
        result = await connected_cache.get_batch([], "model")
        assert result == {}

    async def test_batch_get_returns_hits(self, connected_cache):
        emb_a = [0.1, 0.2]
        emb_b = [0.3, 0.4]

        mock_pipe = AsyncMock()
        mock_pipe.get = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(
            return_value=[json.dumps(emb_a), None, json.dumps(emb_b)]
        )
        connected_cache.client.pipeline = MagicMock(return_value=mock_pipe)

        result = await connected_cache.get_batch(["a", "b", "c"], "model")
        assert result == {0: emb_a, 2: emb_b}

    async def test_batch_get_handles_redis_error(self, connected_cache):
        from redis.exceptions import RedisError

        connected_cache.client.pipeline = MagicMock(side_effect=RedisError("fail"))

        result = await connected_cache.get_batch(["a"], "model")
        assert result == {}


class TestBatchSet:
    """Test batch set operation."""

    async def test_batch_set_noop_when_not_connected(self, cache):
        await cache.set_batch(["a"], "model", [[0.1]])

    async def test_batch_set_noop_for_empty_input(self, connected_cache):
        mock_pipe = AsyncMock()
        connected_cache.client.pipeline = MagicMock(return_value=mock_pipe)

        await connected_cache.set_batch([], "model", [])
        mock_pipe.execute.assert_not_awaited()

    async def test_batch_set_uses_pipeline(self, connected_cache):
        mock_pipe = AsyncMock()
        mock_pipe.set = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[True, True])
        connected_cache.client.pipeline = MagicMock(return_value=mock_pipe)

        texts = ["hello", "world"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        await connected_cache.set_batch(texts, "model", embeddings)

        assert mock_pipe.set.call_count == 2
        mock_pipe.execute.assert_awaited_once()

    async def test_batch_set_handles_redis_error(self, connected_cache):
        from redis.exceptions import RedisError

        connected_cache.client.pipeline = MagicMock(side_effect=RedisError("fail"))

        # Should not raise
        await connected_cache.set_batch(["a"], "model", [[0.1]])


class TestConnect:
    """Test connect/disconnect."""

    async def test_connect_with_empty_url(self):
        cache = EmbeddingCache(redis_url="", ttl_seconds=100)
        await cache.connect()
        assert cache.client is None

    async def test_disconnect_when_not_connected(self, cache):
        await cache.disconnect()
        assert cache.client is None

    async def test_disconnect_closes_client(self, connected_cache):
        await connected_cache.disconnect()
        assert connected_cache.client is None

    @patch("rag_config_common.cache.embedding_cache.REDIS_AVAILABLE", False)
    async def test_connect_without_redis_package(self):
        cache = EmbeddingCache(redis_url="redis://localhost:6379/0")
        await cache.connect()
        assert cache.client is None


class TestGracefulDegradation:
    """Test graceful degradation when Redis is unavailable."""

    async def test_all_operations_noop_when_disconnected(self, cache):
        """All operations should silently no-op when not connected."""
        assert await cache.get("t", "m") is None
        assert await cache.get_batch(["t"], "m") == {}
        await cache.set("t", "m", [0.1])
        await cache.set_batch(["t"], "m", [[0.1]])
