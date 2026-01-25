"""Base chunker interface and common data structures."""

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for text chunking."""

    # Size parameters
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100

    # Behavior flags
    strip_whitespace: bool = True
    preserve_separators: bool = False

    # Semantic chunking parameters
    sentence_min_length: int = 20
    combine_short_sentences: bool = True

    # Metadata options
    include_position: bool = True
    include_hash: bool = True

    def validate(self) -> None:
        """Validate configuration parameters."""
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        if self.min_chunk_size < 0:
            raise ValueError("min_chunk_size cannot be negative")


@dataclass
class Chunk:
    """A chunk of text from a document."""

    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Position information
    chunk_index: int = 0
    start_char: int = 0
    end_char: int = 0

    # Content hash for deduplication
    content_hash: str = ""

    def __post_init__(self):
        """Generate content hash if not provided."""
        if not self.content_hash and self.content:
            self.content_hash = self._generate_hash()

    def _generate_hash(self) -> str:
        """Generate MD5 hash of content."""
        return hashlib.md5(self.content.encode("utf-8")).hexdigest()

    @property
    def char_count(self) -> int:
        """Get character count."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "content_hash": self.content_hash,
            "char_count": self.char_count,
            "word_count": self.word_count,
        }


class BaseChunker(ABC):
    """Abstract base class for text chunkers."""

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize chunker with optional config."""
        self.config = config or ChunkingConfig()
        self.config.validate()
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def chunk(
        self,
        text: str,
        config: Optional[ChunkingConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Split text into chunks.

        Args:
            text: The text to split
            config: Optional chunking configuration (overrides instance config)
            metadata: Optional metadata to include in each chunk

        Returns:
            List of Chunk objects
        """
        pass

    def _create_chunk(
        self,
        content: str,
        index: int,
        start_char: int,
        end_char: int,
        base_metadata: Optional[Dict[str, Any]] = None,
    ) -> Chunk:
        """Create a chunk with metadata."""
        metadata = dict(base_metadata) if base_metadata else {}

        if self.config.include_position:
            metadata["position"] = {
                "start": start_char,
                "end": end_char,
                "index": index,
            }

        chunk = Chunk(
            content=content,
            metadata=metadata,
            chunk_index=index,
            start_char=start_char,
            end_char=end_char,
        )

        if not self.config.include_hash:
            chunk.content_hash = ""

        return chunk

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text before chunking."""
        if self.config.strip_whitespace:
            # Normalize whitespace but preserve paragraph breaks
            lines = text.split("\n")
            lines = [line.strip() for line in lines]
            text = "\n".join(lines)

        return text

    def _filter_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Filter out chunks that are too small."""
        return [
            chunk
            for chunk in chunks
            if len(chunk.content.strip()) >= self.config.min_chunk_size
        ]
