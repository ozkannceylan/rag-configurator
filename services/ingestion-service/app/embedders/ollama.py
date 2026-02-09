"""Ollama embedding provider for local models."""

import logging
import time
from typing import Dict, List, Optional

import httpx

from app.embedders.base import BaseEmbedder, EmbeddingConfig, EmbeddingResult

logger = logging.getLogger(__name__)

# Default Ollama settings
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "nomic-embed-text"

# Known model dimensions
OLLAMA_MODEL_DIMENSIONS: Dict[str, int] = {
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "all-minilm": 384,
    "snowflake-arctic-embed": 1024,
}


class OllamaEmbedder(BaseEmbedder):
    """
    Ollama embedding provider for local models.

    Uses the Ollama API to generate embeddings with models like
    nomic-embed-text running locally.
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initialize Ollama embedder.

        Args:
            config: Embedding configuration with base_url and model settings
        """
        super().__init__(config)

        # Set defaults for Ollama - override base class defaults
        if not self.config.model or self.config.model == "text-embedding-3-small":
            self.config.model = DEFAULT_OLLAMA_MODEL
        if not self.config.base_url:
            self.config.base_url = DEFAULT_OLLAMA_URL

        self._dimensions: Optional[int] = None

    @property
    def dimensions(self) -> int:
        """Get embedding dimensions for the current model."""
        if self._dimensions is not None:
            return self._dimensions

        if self.config.dimensions:
            return self.config.dimensions

        # Look up known model dimensions
        dims = OLLAMA_MODEL_DIMENSIONS.get(self.config.model)
        if dims:
            return dims

        # Default for unknown models
        return 768

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self.config.model

    async def embed(
        self, texts: List[str], config: Optional[EmbeddingConfig] = None
    ) -> EmbeddingResult:
        """
        Generate embeddings using Ollama API.

        Args:
            texts: List of texts to embed
            config: Optional configuration override

        Returns:
            EmbeddingResult with embeddings
        """
        cfg = config or self.config
        start_time = time.time()

        # Validate and clean texts
        texts = self._validate_texts(texts)
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                model=cfg.model,
                dimensions=self.dimensions,
            )

        # Build API URL - use /api/embed for batch embedding
        api_url = f"{cfg.base_url.rstrip('/')}/api/embed"

        all_embeddings = []

        async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
            # Batch texts for efficiency (Ollama supports multiple inputs)
            for batch_start in range(0, len(texts), cfg.batch_size):
                batch = texts[batch_start : batch_start + cfg.batch_size]
                self.logger.debug(
                    f"Processing batch {batch_start // cfg.batch_size + 1}, "
                    f"texts {batch_start + 1}-{batch_start + len(batch)}/{len(texts)}"
                )

                for attempt in range(cfg.max_retries):
                    try:
                        response = await client.post(
                            api_url,
                            json={
                                "model": cfg.model,
                                "input": batch,
                            },
                        )
                        response.raise_for_status()

                        data = response.json()
                        embeddings = data.get("embeddings", [])

                        if not embeddings:
                            raise ValueError("No embeddings returned from Ollama")

                        all_embeddings.extend(embeddings)

                        # Update dimensions from response
                        if self._dimensions is None and embeddings:
                            self._dimensions = len(embeddings[0])

                        break  # Success

                    except httpx.HTTPStatusError as e:
                        self.logger.warning(
                            f"Batch {batch_start // cfg.batch_size + 1} attempt {attempt + 1} failed: "
                            f"HTTP {e.response.status_code}"
                        )
                        if attempt < cfg.max_retries - 1:
                            import asyncio

                            await asyncio.sleep(cfg.retry_delay)
                        else:
                            raise RuntimeError(
                                f"Ollama API error: {e.response.status_code}"
                            )

                    except httpx.ConnectError:
                        raise RuntimeError(
                            f"Cannot connect to Ollama at {cfg.base_url}. "
                            "Make sure Ollama is running."
                        )

                    except Exception as e:
                        self.logger.warning(
                            f"Batch {batch_start // cfg.batch_size + 1} attempt {attempt + 1} failed: {e}"
                        )
                        if attempt < cfg.max_retries - 1:
                            import asyncio

                            await asyncio.sleep(cfg.retry_delay)
                        else:
                            raise

        processing_time = (time.time() - start_time) * 1000

        return EmbeddingResult(
            embeddings=all_embeddings,
            model=cfg.model,
            dimensions=self._dimensions or self.dimensions,
            processing_time_ms=processing_time,
            metadata={
                "provider": "ollama",
                "base_url": cfg.base_url,
            },
        )

    async def check_model_available(self) -> bool:
        """
        Check if the configured model is available in Ollama.

        Returns:
            True if model is available
        """
        try:
            api_url = f"{self.config.base_url.rstrip('/')}/api/tags"

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(api_url)
                response.raise_for_status()

                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]

                # Check if our model is in the list
                return any(self.config.model in m for m in models)

        except Exception as e:
            self.logger.warning(f"Could not check Ollama models: {e}")
            return False

    async def pull_model(self) -> bool:
        """
        Pull the configured model in Ollama.

        Returns:
            True if successful
        """
        try:
            api_url = f"{self.config.base_url.rstrip('/')}/api/pull"

            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    api_url,
                    json={"name": self.config.model},
                )
                response.raise_for_status()
                return True

        except Exception as e:
            self.logger.error(f"Failed to pull model {self.config.model}: {e}")
            return False
