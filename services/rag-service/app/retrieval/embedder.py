"""Embedding utilities for retrieval."""

import logging

import httpx

from app.core.settings import settings

logger = logging.getLogger(__name__)


class QueryEmbedder:
    """Generates embeddings for queries."""

    def __init__(
        self,
        provider: str = "openai",
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """
        Initialize query embedder.

        Args:
            provider: Embedding provider (openai, ollama, etc.)
            model: Model name
            api_key: API key for provider
            base_url: Base URL for provider API
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a query.

        Args:
            query: Query text

        Returns:
            Embedding vector
        """
        if not query or not query.strip():
            return []

        if self.provider == "openai":
            return await self._embed_openai(query)
        elif self.provider == "ollama":
            return await self._embed_ollama(query)
        elif self.provider == "anthropic":
            # Anthropic doesn't have embeddings, fall back to OpenAI
            logger.warning("Anthropic doesn't support embeddings, using OpenAI")
            return await self._embed_openai(query)
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        if self.provider == "openai":
            return await self._embed_openai_batch(texts)
        else:
            # Fall back to sequential for other providers
            results = []
            for text in texts:
                embedding = await self.embed_query(text)
                results.append(embedding)
            return results

    async def _embed_openai(self, text: str) -> list[float]:
        """Generate embedding using OpenAI API."""
        client = await self._get_client()

        api_key = self.api_key or settings.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key not configured")

        base_url = (
            self.base_url or settings.openai_base_url or "https://api.openai.com/v1"
        )
        url = f"{base_url}/embeddings"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": text,
        }

        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            return []

    async def _embed_openai_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts using OpenAI API."""
        client = await self._get_client()

        api_key = self.api_key or settings.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key not configured")

        base_url = (
            self.base_url or settings.openai_base_url or "https://api.openai.com/v1"
        )
        url = f"{base_url}/embeddings"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
        }

        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Sort by index to maintain order
            embeddings_data = sorted(data["data"], key=lambda x: x["index"])
            return [e["embedding"] for e in embeddings_data]
        except Exception as e:
            logger.error(f"OpenAI batch embedding error: {e}")
            return [[] for _ in texts]

    async def _embed_ollama(self, text: str) -> list[float]:
        """Generate embedding using Ollama API."""
        client = await self._get_client()

        base_url = self.base_url or settings.ollama_base_url
        url = f"{base_url}/api/embeddings"

        payload = {
            "model": self.model,
            "prompt": text,
        }

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
        except Exception as e:
            logger.error(f"Ollama embedding error: {e}")
            return []


async def get_embedder(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> QueryEmbedder:
    """
    Get an embedder instance.

    Args:
        provider: Embedding provider (defaults to settings)
        model: Model name (defaults to settings)
        api_key: API key (defaults to settings)

    Returns:
        QueryEmbedder instance
    """
    return QueryEmbedder(
        provider=provider or settings.embedding_provider,
        model=model or settings.embedding_model,
        api_key=api_key,
    )
