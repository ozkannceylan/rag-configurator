"""OpenAI embedding provider."""

import asyncio
import logging
import time

from app.embedders.base import BaseEmbedder, EmbeddingConfig, EmbeddingResult

logger = logging.getLogger(__name__)

# Model dimension mappings
OPENAI_MODEL_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}

# Maximum texts per API request
MAX_BATCH_SIZE = 2048


class OpenAIEmbedder(BaseEmbedder):
    """
    OpenAI embedding provider.

    Uses the OpenAI API to generate embeddings with models like
    text-embedding-3-small and text-embedding-3-large.
    """

    def __init__(self, config: EmbeddingConfig | None = None):
        """
        Initialize OpenAI embedder.

        Args:
            config: Embedding configuration with API key and model settings
        """
        super().__init__(config)

        # Set default model if not specified
        if not self.config.model:
            self.config.model = "text-embedding-3-small"

        # Limit batch size to API maximum
        if self.config.batch_size > MAX_BATCH_SIZE:
            self.config.batch_size = MAX_BATCH_SIZE

        self._client = None
        self._dimensions: int | None = None

    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as err:
                raise ImportError(
                    "OpenAI SDK not installed. Install with: pip install openai"
                ) from err

            # Get API key from config or environment
            api_key = self.config.api_key
            if not api_key:
                from app.core.settings import settings

                api_key = settings.openai_api_key

            if not api_key:
                raise ValueError(
                    "OpenAI API key not configured. "
                    "Set OPENAI_API_KEY environment variable or pass in config."
                )

            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout_seconds,
            )

        return self._client

    @property
    def dimensions(self) -> int:
        """Get embedding dimensions for the current model."""
        if self._dimensions is not None:
            return self._dimensions

        # Check if dimensions specified in config
        if self.config.dimensions:
            return self.config.dimensions

        # Look up model dimensions
        dims = OPENAI_MODEL_DIMENSIONS.get(self.config.model)
        if dims:
            return dims

        # Default for unknown models
        return 1536

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self.config.model

    async def embed(
        self, texts: list[str], config: EmbeddingConfig | None = None
    ) -> EmbeddingResult:
        """
        Generate embeddings using OpenAI API.

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

        client = self._get_client()

        # Process in batches
        all_embeddings = []
        total_tokens = 0
        batches = self._batch_texts(texts, min(cfg.batch_size, MAX_BATCH_SIZE))

        for batch_idx, batch in enumerate(batches):
            self.logger.debug(
                f"Processing batch {batch_idx + 1}/{len(batches)} "
                f"({len(batch)} texts)"
            )

            # Retry logic
            for attempt in range(cfg.max_retries):
                try:
                    # Call OpenAI API
                    kwargs = {
                        "model": cfg.model,
                        "input": batch,
                    }

                    # Add dimensions parameter for newer models
                    if cfg.dimensions and cfg.model.startswith("text-embedding-3"):
                        kwargs["dimensions"] = cfg.dimensions

                    response = await client.embeddings.create(**kwargs)

                    # Extract embeddings
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)

                    # Track tokens
                    if hasattr(response, "usage") and response.usage:
                        total_tokens += response.usage.total_tokens

                    # Update dimensions from response if not set
                    if self._dimensions is None and batch_embeddings:
                        self._dimensions = len(batch_embeddings[0])

                    break  # Success, exit retry loop

                except Exception as e:
                    self.logger.warning(
                        f"Batch {batch_idx + 1} attempt {attempt + 1} failed: {e}"
                    )
                    if attempt < cfg.max_retries - 1:
                        # Exponential backoff
                        delay = cfg.retry_delay * (2**attempt)
                        await asyncio.sleep(delay)
                    else:
                        raise RuntimeError(
                            f"Failed to generate embeddings after {cfg.max_retries} "
                            f"attempts: {e}"
                        ) from e

        processing_time = (time.time() - start_time) * 1000

        return EmbeddingResult(
            embeddings=all_embeddings,
            model=cfg.model,
            dimensions=self._dimensions or self.dimensions,
            total_tokens=total_tokens,
            processing_time_ms=processing_time,
            metadata={
                "provider": "openai",
                "batch_count": len(batches),
            },
        )
