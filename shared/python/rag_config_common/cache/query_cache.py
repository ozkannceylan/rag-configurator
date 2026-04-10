"""Redis-backed cache for RAG query responses."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

try:
    from redis.asyncio import Redis, from_url
    from redis.exceptions import RedisError

    REDIS_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    Redis = Any
    from_url = None
    RedisError = Exception
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class QueryCache:
    """Redis-backed cache for RAG query responses."""

    def __init__(
        self,
        redis_url: str,
        default_ttl_seconds: int = 300,
        key_prefix: str = "query_cache",
    ):
        self.redis_url = redis_url
        self.default_ttl_seconds = default_ttl_seconds
        self.key_prefix = key_prefix
        self.client: Optional[Redis] = None

    async def connect(self) -> None:
        """Connect to Redis. Graceful fallback if unavailable."""
        if not self.redis_url:
            logger.warning("REDIS_URL is empty, query cache disabled")
            return

        if not REDIS_AVAILABLE or from_url is None:
            logger.warning(
                "redis package is not installed, query cache disabled"
            )
            return

        candidate = from_url(self.redis_url, decode_responses=True)
        try:
            await candidate.ping()
            self.client = candidate
            logger.info("Query cache connected to Redis")
        except Exception as exc:
            logger.warning("Redis unavailable for query cache: %s", exc)
            await candidate.aclose()

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    def _cache_key(self, config_id: str, query: str) -> str:
        """Generate key: prefix:config_id:sha256(query)."""
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        return f"{self.key_prefix}:{config_id}:{query_hash}"

    async def get(self, config_id: str, query: str) -> Optional[dict]:
        """Get cached query response. Returns None on miss."""
        if self.client is None:
            return None

        try:
            data = await self.client.get(self._cache_key(config_id, query))
            if data is not None:
                return json.loads(data)
            return None
        except (RedisError, json.JSONDecodeError) as exc:
            logger.warning("Query cache get failed: %s", exc)
            return None

    async def set(
        self,
        config_id: str,
        query: str,
        response: dict,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Cache a query response with TTL."""
        if self.client is None:
            return

        try:
            key = self._cache_key(config_id, query)
            ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
            await self.client.set(key, json.dumps(response), ex=ttl)
        except (RedisError, TypeError) as exc:
            logger.warning("Query cache set failed: %s", exc)

    async def invalidate_config(self, config_id: str) -> None:
        """Invalidate all cached queries for a config (uses SCAN pattern)."""
        if self.client is None:
            return

        try:
            pattern = f"{self.key_prefix}:{config_id}:*"
            cursor = 0
            while True:
                cursor, keys = await self.client.scan(
                    cursor=cursor, match=pattern, count=100
                )
                if keys:
                    await self.client.delete(*keys)
                if cursor == 0:
                    break
        except RedisError as exc:
            logger.warning("Query cache invalidation failed: %s", exc)
