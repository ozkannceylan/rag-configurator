"""HuggingFace sentence-transformers embedding provider."""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from app.embedders.base import BaseEmbedder, EmbeddingConfig, EmbeddingResult

logger = logging.getLogger(__name__)

# Default model
DEFAULT_HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Known model dimensions
HF_MODEL_DIMENSIONS: Dict[str, int] = {
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
    "sentence-transformers/paraphrase-MiniLM-L6-v2": 384,
    "sentence-transformers/multi-qa-mpnet-base-dot-v1": 768,
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
    "BAAI/bge-large-en-v1.5": 1024,
    "intfloat/e5-small-v2": 384,
    "intfloat/e5-base-v2": 768,
    "intfloat/e5-large-v2": 1024,
}


class HuggingFaceEmbedder(BaseEmbedder):
    """
    HuggingFace sentence-transformers embedding provider.

    Uses sentence-transformers library to generate embeddings locally
    with models like all-MiniLM-L6-v2.
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initialize HuggingFace embedder.

        Args:
            config: Embedding configuration with model settings
        """
        super().__init__(config)

        # Set default model
        if not self.config.model:
            self.config.model = DEFAULT_HF_MODEL

        self._model = None
        self._dimensions: Optional[int] = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _get_model(self):
        """Get or create sentence-transformers model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )

            self.logger.info(f"Loading model: {self.config.model}")
            self._model = SentenceTransformer(self.config.model)

            # Get actual dimensions from model
            self._dimensions = self._model.get_sentence_embedding_dimension()
            self.logger.info(
                f"Model loaded with {self._dimensions} dimensions"
            )

        return self._model

    @property
    def dimensions(self) -> int:
        """Get embedding dimensions for the current model."""
        if self._dimensions is not None:
            return self._dimensions

        if self.config.dimensions:
            return self.config.dimensions

        # Look up known model dimensions
        dims = HF_MODEL_DIMENSIONS.get(self.config.model)
        if dims:
            return dims

        # Default for unknown models
        return 384

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self.config.model

    async def embed(
        self, texts: List[str], config: Optional[EmbeddingConfig] = None
    ) -> EmbeddingResult:
        """
        Generate embeddings using sentence-transformers.

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

        # Run embedding in thread pool (sentence-transformers is sync)
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            self._executor,
            self._embed_sync,
            texts,
            cfg,
        )

        processing_time = (time.time() - start_time) * 1000

        return EmbeddingResult(
            embeddings=embeddings,
            model=cfg.model,
            dimensions=self._dimensions or self.dimensions,
            processing_time_ms=processing_time,
            metadata={
                "provider": "huggingface",
                "model_type": "sentence-transformers",
            },
        )

    def _embed_sync(
        self, texts: List[str], config: EmbeddingConfig
    ) -> List[List[float]]:
        """
        Synchronous embedding generation.

        Args:
            texts: List of texts to embed
            config: Embedding configuration

        Returns:
            List of embedding vectors
        """
        model = self._get_model()

        # Process in batches
        all_embeddings = []
        batches = self._batch_texts(texts, config.batch_size)

        for batch in batches:
            # Generate embeddings
            embeddings = model.encode(
                batch,
                normalize_embeddings=config.normalize,
                show_progress_bar=False,
            )

            # Convert numpy arrays to lists
            for embedding in embeddings:
                all_embeddings.append(embedding.tolist())

        return all_embeddings

    def unload_model(self):
        """Unload the model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            self.logger.info("Model unloaded")

            # Try to free GPU memory if using CUDA
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass


class HuggingFaceAPIEmbedder(BaseEmbedder):
    """
    HuggingFace Inference API embedding provider.

    Uses the HuggingFace Inference API for embeddings without
    loading models locally.
    """

    HF_API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction"

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initialize HuggingFace API embedder.

        Args:
            config: Embedding configuration with API key
        """
        super().__init__(config)

        if not self.config.model:
            self.config.model = DEFAULT_HF_MODEL

        self._dimensions: Optional[int] = None

    @property
    def dimensions(self) -> int:
        """Get embedding dimensions."""
        if self._dimensions is not None:
            return self._dimensions

        if self.config.dimensions:
            return self.config.dimensions

        dims = HF_MODEL_DIMENSIONS.get(self.config.model)
        return dims or 384

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self.config.model

    async def embed(
        self, texts: List[str], config: Optional[EmbeddingConfig] = None
    ) -> EmbeddingResult:
        """
        Generate embeddings using HuggingFace Inference API.

        Args:
            texts: List of texts to embed
            config: Optional configuration override

        Returns:
            EmbeddingResult with embeddings
        """
        import httpx

        cfg = config or self.config
        start_time = time.time()

        texts = self._validate_texts(texts)
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                model=cfg.model,
                dimensions=self.dimensions,
            )

        # Get API key
        api_key = cfg.api_key
        if not api_key:
            raise ValueError(
                "HuggingFace API key required. "
                "Set api_key in config or HF_API_KEY environment variable."
            )

        api_url = f"{self.HF_API_URL}/{cfg.model}"
        headers = {"Authorization": f"Bearer {api_key}"}

        all_embeddings = []

        async with httpx.AsyncClient(timeout=cfg.timeout_seconds) as client:
            # Process in batches
            batches = self._batch_texts(texts, cfg.batch_size)

            for batch in batches:
                for attempt in range(cfg.max_retries):
                    try:
                        response = await client.post(
                            api_url,
                            headers=headers,
                            json={"inputs": batch, "options": {"wait_for_model": True}},
                        )
                        response.raise_for_status()

                        embeddings = response.json()

                        # Handle nested response format
                        for emb in embeddings:
                            if isinstance(emb[0], list):
                                # Mean pooling for token embeddings
                                import numpy as np

                                pooled = np.mean(emb, axis=0).tolist()
                                all_embeddings.append(pooled)
                            else:
                                all_embeddings.append(emb)

                        if self._dimensions is None and all_embeddings:
                            self._dimensions = len(all_embeddings[0])

                        break

                    except Exception as e:
                        if attempt < cfg.max_retries - 1:
                            await asyncio.sleep(cfg.retry_delay)
                        else:
                            raise RuntimeError(f"HuggingFace API error: {e}")

        processing_time = (time.time() - start_time) * 1000

        return EmbeddingResult(
            embeddings=all_embeddings,
            model=cfg.model,
            dimensions=self._dimensions or self.dimensions,
            processing_time_ms=processing_time,
            metadata={
                "provider": "huggingface_api",
            },
        )
