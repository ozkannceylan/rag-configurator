"""Recursive character text splitter."""

import logging
from typing import Any, Dict, List, Optional

from app.chunkers.base import BaseChunker, Chunk, ChunkingConfig

logger = logging.getLogger(__name__)


class RecursiveChunker(BaseChunker):
    """
    Recursive character text splitter.

    Splits text by trying separators in order of priority:
    1. Double newlines (paragraph breaks)
    2. Single newlines
    3. Spaces
    4. Empty string (character by character)

    Respects chunk_size and chunk_overlap settings.
    """

    # Default separators in order of priority
    DEFAULT_SEPARATORS = ["\n\n", "\n", " ", ""]

    def __init__(
        self,
        config: Optional[ChunkingConfig] = None,
        separators: Optional[List[str]] = None,
    ):
        """
        Initialize recursive chunker.

        Args:
            config: Chunking configuration
            separators: Custom list of separators in priority order
        """
        super().__init__(config)
        self.separators = separators or self.DEFAULT_SEPARATORS

    def chunk(
        self,
        text: str,
        config: Optional[ChunkingConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Split text into chunks using recursive character splitting.

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

        # Split text recursively
        splits = self._split_text(text, self.separators, cfg)

        # Create chunks with overlap
        chunks = self._create_chunks_with_overlap(splits, cfg, metadata)

        # Filter out small chunks
        chunks = self._filter_chunks(chunks)

        return chunks

    def _split_text(
        self, text: str, separators: List[str], config: ChunkingConfig
    ) -> List[str]:
        """
        Recursively split text using separators.

        Args:
            text: Text to split
            separators: List of separators to try
            config: Chunking configuration

        Returns:
            List of text segments
        """
        final_chunks = []

        # Find the appropriate separator
        separator = separators[-1]  # Default to last (usually empty string)
        new_separators = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1 :]
                break

        # Split by the separator
        if separator:
            splits = text.split(separator)
        else:
            # Character by character split
            splits = list(text)

        # Process each split
        good_splits = []
        current_sep = separator if config.preserve_separators else ""

        for split in splits:
            if len(split) < config.chunk_size:
                good_splits.append(split)
            else:
                # Need to split further
                if good_splits:
                    merged = self._merge_splits(good_splits, current_sep, config)
                    final_chunks.extend(merged)
                    good_splits = []

                if new_separators:
                    # Recursively split with remaining separators
                    sub_splits = self._split_text(split, new_separators, config)
                    final_chunks.extend(sub_splits)
                else:
                    # Can't split further, just add as is
                    final_chunks.append(split)

        # Merge remaining good splits
        if good_splits:
            merged = self._merge_splits(good_splits, current_sep, config)
            final_chunks.extend(merged)

        return final_chunks

    def _merge_splits(
        self, splits: List[str], separator: str, config: ChunkingConfig
    ) -> List[str]:
        """
        Merge small splits into larger chunks.

        Args:
            splits: List of text splits
            separator: Separator to use when joining
            config: Chunking configuration

        Returns:
            List of merged text segments
        """
        merged_chunks = []
        current_chunk = []
        current_length = 0

        for split in splits:
            split_length = len(split)

            # Calculate length with separator
            separator_length = len(separator) if current_chunk else 0
            total_length = current_length + split_length + separator_length

            if total_length > config.chunk_size:
                # Current chunk is full, save it
                if current_chunk:
                    merged_chunks.append(separator.join(current_chunk))
                current_chunk = [split]
                current_length = split_length
            else:
                current_chunk.append(split)
                current_length = total_length

        # Don't forget the last chunk
        if current_chunk:
            merged_chunks.append(separator.join(current_chunk))

        return merged_chunks

    def _create_chunks_with_overlap(
        self,
        splits: List[str],
        config: ChunkingConfig,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Create chunks with overlap from splits.

        Args:
            splits: List of text splits
            config: Chunking configuration
            metadata: Base metadata for chunks

        Returns:
            List of Chunk objects
        """
        if not splits:
            return []

        chunks = []
        current_position = 0

        for i, split in enumerate(splits):
            # Calculate overlap from previous chunk
            overlap_text = ""
            if i > 0 and config.chunk_overlap > 0:
                # Get overlap from previous split
                prev_split = splits[i - 1]
                overlap_start = max(0, len(prev_split) - config.chunk_overlap)
                overlap_text = prev_split[overlap_start:]

            # Combine overlap with current split
            if overlap_text:
                content = overlap_text + " " + split
                start_char = current_position - len(overlap_text) - 1
            else:
                content = split
                start_char = current_position

            end_char = current_position + len(split)

            # Create chunk
            chunk = self._create_chunk(
                content=content.strip(),
                index=i,
                start_char=max(0, start_char),
                end_char=end_char,
                base_metadata=metadata,
            )
            chunks.append(chunk)

            # Update position (account for separator)
            current_position = end_char + 1

        return chunks
