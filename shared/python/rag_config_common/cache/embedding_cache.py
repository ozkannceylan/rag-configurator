"""Redis-backed cache for embedding vectors to avoid recomputation."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

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


class EmbeddingCache:
    """Redis-backed cache for embedding vectors to avoid recomputation."""

    def __init__(
        self,
        redis_url: str,
        ttl_seconds: int = 3600,
        key_prefix: str = "emb_cache",
    ):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
        self.client: Optional[Redis] = None

    async def connect(self) -> None:
        """Connect to Redis. Graceful fallback if unavailable."""
        if not self.redis_url:
            logger.warning("REDIS_URL is empty, embedding cache disabled")
            return

        if not REDIS_AVAILABLE or from_url is None:
            logger.warning(
                "redis package is not installed, embedding cache disabled"
            )
            return

        candidate = from_url(self.redis_url, decode_responses=True)
        try:
            await candidate.ping()
            self.client = candidate
            logger.info("Embedding cache connected to Redis")
        except Exception as exc:
            logger.warning(
                "Redis unavailable for embedding cache: %s", exc
            )
            await candidate.aclose()

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    def _cache_key(self, text: str, model: str) -> str:
        """Generate cache key: prefix:model:sha256(text)."""
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self.key_prefix}:{model}:{text_hash}"

    async def get(self, text: str, model: str) -> Optional[List[float]]:
        """Get cached embedding for text+model. Returns None on miss."""
        if self.client is None:
            return None

        try:
            data = await self.client.get(self._cache_key(text, model))
            if data is not None:
                return json.loads(data)
            return None
        except (RedisError, json.JSONDecodeError) as exc:
            logger.warning("Embedding cache get failed: %s", exc)
            return None

    async def set(self, text: str, model: str, embedding: List[float]) -> None:
        """Cache an embedding with TTL."""
        if self.client is None:
            return

        try:
            key = self._cache_key(text, model)
            await self.client.set(key, json.dumps(embedding), ex=self.ttl_seconds)
        except RedisError as exc:
            logger.warning("Embedding cache set failed: %s", exc)

    async def get_batch(
        self, texts: List[str], model: str
    ) -> Dict[int, List[float]]:
        """
        Get cached embeddings for multiple texts.

        Returns dict of index -> embedding for cache hits.
        Uses Redis pipeline for efficiency.
        """
        if self.client is None or not texts:
            return {}

        try:
            keys = [self._cache_key(text, model) for text in texts]
            pipe = self.client.pipeline(transaction=False)
            for key in keys:
                pipe.get(key)
            results = await pipe.execute()

            hits: Dict[int, List[float]] = {}
            for i, data in enumerate(results):
                if data is not None:
                    try:
                        hits[i] = json.loads(data)
                    except json.JSONDecodeError:
                        pass
            return hits
        except RedisError as exc:
            logger.warning("Embedding cache batch get failed: %s", exc)
            return {}

    async def set_batch(
        self, texts: List[str], model: str, embeddings: List[List[float]]
    ) -> None:
        """Cache multiple embeddings with TTL. Uses Redis pipeline."""
        if self.client is None or not texts:
            return

        try:
            pipe = self.client.pipeline(transaction=False)
            for text, embedding in zip(texts, embeddings):
                key = self._cache_key(text, model)
                pipe.set(key, json.dumps(embedding), ex=self.ttl_seconds)
            await pipe.execute()
        except RedisError as exc:
            logger.warning("Embedding cache batch set failed: %s", exc)
