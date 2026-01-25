"""Document-level chunker that returns the entire document as one chunk."""

import logging
from typing import Any, Dict, List, Optional

from app.chunkers.base import BaseChunker, Chunk, ChunkingConfig

logger = logging.getLogger(__name__)


class DocumentChunker(BaseChunker):
    """
    Document-level chunker that treats the entire document as a single chunk.

    Useful for:
    - Small documents that don't need splitting
    - Documents where context should be preserved entirely
    - Testing and debugging
    """

    def chunk(
        self,
        text: str,
        config: Optional[ChunkingConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Return the entire document as a single chunk.

        Args:
            text: The text to process
            config: Optional chunking configuration (mostly ignored)
            metadata: Optional metadata to include in the chunk

        Returns:
            List containing a single Chunk with the entire document
        """
        if not text:
            return []

        # Preprocess text
        text = self._preprocess_text(text)

        # Check if document is too large
        cfg = config or self.config
        if len(text) > cfg.chunk_size * 10:  # Warn if very large
            logger.warning(
                f"Document is large ({len(text)} chars) but not being split. "
                f"Consider using RecursiveChunker or SemanticChunker."
            )

        # Create single chunk
        chunk = self._create_chunk(
            content=text,
            index=0,
            start_char=0,
            end_char=len(text),
            base_metadata=metadata,
        )

        return [chunk]


class ParagraphChunker(BaseChunker):
    """
    Paragraph-level chunker that splits by double newlines.

    Each paragraph becomes a separate chunk. Useful for
    documents with clear paragraph structure.
    """

    def chunk(
        self,
        text: str,
        config: Optional[ChunkingConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Split document into paragraphs.

        Args:
            text: The text to split
            config: Optional chunking configuration
            metadata: Optional metadata to include in each chunk

        Returns:
            List of Chunk objects, one per paragraph
        """
        cfg = config or self.config

        if not text:
            return []

        # Preprocess text
        text = self._preprocess_text(text)

        # Split by double newlines (paragraph breaks)
        paragraphs = text.split("\n\n")

        chunks = []
        current_position = 0

        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Find actual position in text
            start_char = text.find(paragraph, current_position)
            if start_char == -1:
                start_char = current_position
            end_char = start_char + len(paragraph)

            # Skip if paragraph is too small
            if len(paragraph) < cfg.min_chunk_size:
                current_position = end_char + 2  # +2 for \n\n
                continue

            # Create chunk
            chunk = self._create_chunk(
                content=paragraph,
                index=len(chunks),
                start_char=start_char,
                end_char=end_char,
                base_metadata=metadata,
            )
            chunks.append(chunk)

            current_position = end_char + 2  # +2 for \n\n

        return chunks


class FixedSizeChunker(BaseChunker):
    """
    Fixed-size chunker that splits text into equal-sized chunks.

    Simpler than recursive chunker - just splits at fixed intervals
    with optional overlap. Does not respect word or sentence boundaries.
    """

    def chunk(
        self,
        text: str,
        config: Optional[ChunkingConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Split text into fixed-size chunks.

        Args:
            text: The text to split
            config: Optional chunking configuration
            metadata: Optional metadata to include in each chunk

        Returns:
            List of Chunk objects
        """
        cfg = config or self.config

        if not text:
            return []

        # Preprocess text
        text = self._preprocess_text(text)

        chunks = []
        step = cfg.chunk_size - cfg.chunk_overlap
        if step <= 0:
            step = cfg.chunk_size

        i = 0
        chunk_index = 0

        while i < len(text):
            # Extract chunk
            end = min(i + cfg.chunk_size, len(text))
            content = text[i:end]

            # Create chunk
            chunk = self._create_chunk(
                content=content.strip(),
                index=chunk_index,
                start_char=i,
                end_char=end,
                base_metadata=metadata,
            )

            # Only add if meets minimum size (or it's the last chunk)
            if len(content.strip()) >= cfg.min_chunk_size or end == len(text):
                chunks.append(chunk)
                chunk_index += 1

            i += step

        return chunks
