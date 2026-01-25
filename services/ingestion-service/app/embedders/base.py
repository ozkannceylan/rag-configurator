"""Base embedder interface and common data structures."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""

    # Model settings
    model: str = "text-embedding-3-small"
    dimensions: Optional[int] = None  # None = use model default

    # API settings
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    # Batch settings
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0

    # Timeout settings
    timeout_seconds: int = 60

    # Normalization
    normalize: bool = True


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""

    embeddings: List[List[float]]
    model: str
    dimensions: int
    total_tokens: int = 0
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        """Number of embeddings generated."""
        return len(self.embeddings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "embeddings": self.embeddings,
            "model": self.model,
            "dimensions": self.dimensions,
            "total_tokens": self.total_tokens,
            "processing_time_ms": self.processing_time_ms,
            "count": self.count,
            "metadata": self.metadata,
        }


class BaseEmbedder(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """Initialize embedder with optional config."""
        self.config = config or EmbeddingConfig()
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def embed(
        self, texts: List[str], config: Optional[EmbeddingConfig] = None
    ) -> EmbeddingResult:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed
            config: Optional configuration override

        Returns:
            EmbeddingResult with embeddings and metadata
        """
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Get the embedding dimensions for the current model."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name."""
        pass

    async def embed_single(
        self, text: str, config: Optional[EmbeddingConfig] = None
    ) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            config: Optional configuration override

        Returns:
            Embedding vector
        """
        result = await self.embed([text], config)
        return result.embeddings[0] if result.embeddings else []

    def _validate_texts(self, texts: List[str]) -> List[str]:
        """Validate and clean input texts."""
        if not texts:
            return []

        cleaned = []
        for text in texts:
            if text is None:
                self.logger.warning("Skipping None text")
                continue
            text = str(text).strip()
            if text:
                cleaned.append(text)
            else:
                self.logger.warning("Skipping empty text")

        return cleaned

    def _batch_texts(self, texts: List[str], batch_size: int) -> List[List[str]]:
        """Split texts into batches."""
        return [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]
