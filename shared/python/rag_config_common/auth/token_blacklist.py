"""Redis-backed JWT blacklist with in-memory fallback."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

try:
    from redis.asyncio import Redis, from_url
    from redis.exceptions import RedisError

    REDIS_IMPORT_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - depends on runtime environment
    Redis = Any
    from_url = None
    RedisError = Exception
    REDIS_IMPORT_AVAILABLE = False

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """Track revoked JWT IDs in Redis with a safe in-memory fallback."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Optional[Redis] = None
        self._memory_blacklist: dict[str, float] = {}

    async def connect(self) -> None:
        """Initialize a Redis client if the runtime supports it."""
        if not self.redis_url:
            logger.warning("REDIS_URL is empty, using in-memory token blacklist")
            return

        if not REDIS_IMPORT_AVAILABLE or from_url is None:
            logger.warning("redis package unavailable, using in-memory token blacklist")
            return

        candidate = from_url(self.redis_url, decode_responses=True)
        try:
            await candidate.ping()
            self.client = candidate
        except Exception as exc:
            logger.warning(
                "Redis unavailable for token blacklist, using fallback: %s",
                exc,
            )
            await candidate.aclose()

    async def disconnect(self) -> None:
        """Close the Redis client if present."""
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    async def blacklist_token(self, token_id: str, ttl_seconds: int) -> None:
        """Record a revoked token ID until its original expiry time."""
        if not token_id or ttl_seconds <= 0:
            return

        self._memory_blacklist[token_id] = time.time() + ttl_seconds
        if self.client is None:
            return

        try:
            await self.client.set(f"token_blacklist:{token_id}", "1", ex=ttl_seconds)
        except RedisError as exc:
            logger.warning("Failed to persist blacklist entry to Redis: %s", exc)

    async def is_blacklisted(self, token_id: Optional[str]) -> bool:
        """Return True when the token has been revoked."""
        if not token_id:
            return False

        self._cleanup_memory_blacklist()
        if token_id in self._memory_blacklist:
            return True

        if self.client is None:
            return False

        try:
            return bool(await self.client.exists(f"token_blacklist:{token_id}"))
        except RedisError as exc:
            logger.warning("Failed to query token blacklist in Redis: %s", exc)
            return False

    def _cleanup_memory_blacklist(self) -> None:
        """Drop expired in-memory fallback entries."""
        now = time.time()
        expired_ids = [
            token_id
            for token_id, expires_at in self._memory_blacklist.items()
            if expires_at <= now
        ]
        for token_id in expired_ids:
            self._memory_blacklist.pop(token_id, None)
