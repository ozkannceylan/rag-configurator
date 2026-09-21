"""Module-level QueryCache singleton for the RAG service."""

from rag_config_common.cache.query_cache import QueryCache

from app.core.settings import settings

query_cache = QueryCache(settings.redis_url)
