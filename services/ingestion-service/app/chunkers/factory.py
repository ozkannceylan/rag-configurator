"""Factory for creating text chunkers."""

import logging
from enum import Enum
from typing import Optional, Type

from app.chunkers.base import BaseChunker, ChunkingConfig
from app.chunkers.document import DocumentChunker, FixedSizeChunker, ParagraphChunker
from app.chunkers.recursive import RecursiveChunker
from app.chunkers.semantic import SemanticChunker

logger = logging.getLogger(__name__)


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""

    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    DOCUMENT = "document"
    PARAGRAPH = "paragraph"
    FIXED_SIZE = "fixed_size"


# Registry of chunkers by strategy
CHUNKER_REGISTRY: dict[ChunkingStrategy, Type[BaseChunker]] = {
    ChunkingStrategy.RECURSIVE: RecursiveChunker,
    ChunkingStrategy.SEMANTIC: SemanticChunker,
    ChunkingStrategy.DOCUMENT: DocumentChunker,
    ChunkingStrategy.PARAGRAPH: ParagraphChunker,
    ChunkingStrategy.FIXED_SIZE: FixedSizeChunker,
}


def get_chunker(
    strategy: ChunkingStrategy | str = ChunkingStrategy.RECURSIVE,
    config: Optional[ChunkingConfig] = None,
) -> BaseChunker:
    """
    Get a chunker instance for the specified strategy.

    Args:
        strategy: Chunking strategy to use
        config: Optional chunking configuration

    Returns:
        BaseChunker instance

    Raises:
        ValueError: If strategy is not recognized
    """
    # Convert string to enum if needed
    if isinstance(strategy, str):
        try:
            strategy = ChunkingStrategy(strategy.lower())
        except ValueError:
            valid_strategies = [s.value for s in ChunkingStrategy]
            raise ValueError(
                f"Unknown chunking strategy: '{strategy}'. "
                f"Valid strategies: {valid_strategies}"
            )

    chunker_class = CHUNKER_REGISTRY.get(strategy)
    if chunker_class is None:
        raise ValueError(f"No chunker registered for strategy: {strategy}")

    return chunker_class(config)


def get_available_strategies() -> list[str]:
    """Get list of available chunking strategies."""
    return [s.value for s in ChunkingStrategy]


def get_chunker_info() -> dict[str, dict]:
    """
    Get information about all registered chunkers.

    Returns:
        Dictionary with chunker information
    """
    info = {}
    for strategy, chunker_class in CHUNKER_REGISTRY.items():
        info[strategy.value] = {
            "name": chunker_class.__name__,
            "description": chunker_class.__doc__ or "",
        }
    return info


def get_default_config(strategy: ChunkingStrategy | str) -> ChunkingConfig:
    """
    Get recommended default configuration for a strategy.

    Args:
        strategy: Chunking strategy

    Returns:
        ChunkingConfig with recommended settings
    """
    if isinstance(strategy, str):
        strategy = ChunkingStrategy(strategy.lower())

    # Strategy-specific defaults
    if strategy == ChunkingStrategy.SEMANTIC:
        return ChunkingConfig(
            chunk_size=1500,
            chunk_overlap=200,
            min_chunk_size=100,
            sentence_min_length=20,
            combine_short_sentences=True,
        )
    elif strategy == ChunkingStrategy.DOCUMENT:
        return ChunkingConfig(
            chunk_size=50000,  # Large size since we're not splitting
            chunk_overlap=0,
            min_chunk_size=0,
        )
    elif strategy == ChunkingStrategy.PARAGRAPH:
        return ChunkingConfig(
            chunk_size=2000,
            chunk_overlap=0,  # No overlap for paragraphs
            min_chunk_size=50,
        )
    elif strategy == ChunkingStrategy.FIXED_SIZE:
        return ChunkingConfig(
            chunk_size=1000,
            chunk_overlap=100,
            min_chunk_size=50,
        )
    else:
        # Default for recursive
        return ChunkingConfig(
            chunk_size=1000,
            chunk_overlap=200,
            min_chunk_size=100,
        )
