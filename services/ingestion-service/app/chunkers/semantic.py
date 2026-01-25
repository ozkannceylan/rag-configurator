"""Semantic chunker that splits by sentences."""

import logging
import re
from typing import Any, Dict, List, Optional

from app.chunkers.base import BaseChunker, Chunk, ChunkingConfig

logger = logging.getLogger(__name__)


class SemanticChunker(BaseChunker):
    """
    Semantic text chunker that respects sentence boundaries.

    Splits text into sentences first, then groups sentences
    to approach the target chunk_size while keeping semantically
    related content together.
    """

    # Sentence ending patterns
    SENTENCE_ENDINGS = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

    # Additional sentence boundary patterns
    SENTENCE_BOUNDARIES = [
        r"(?<=[.!?])\s+",  # After punctuation with space
        r"(?<=\n)\s*(?=\S)",  # After newline
        r"(?<=:)\s*\n",  # After colon with newline
    ]

    def __init__(self, config: Optional[ChunkingConfig] = None):
        """Initialize semantic chunker."""
        super().__init__(config)

    def chunk(
        self,
        text: str,
        config: Optional[ChunkingConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Split text into semantic chunks based on sentences.

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

        # Split into sentences
        sentences = self._split_into_sentences(text, cfg)

        # Combine short sentences if configured
        if cfg.combine_short_sentences:
            sentences = self._combine_short_sentences(sentences, cfg)

        # Group sentences into chunks
        chunks = self._group_sentences_into_chunks(sentences, cfg, metadata, text)

        # Filter out small chunks
        chunks = self._filter_chunks(chunks)

        return chunks

    def _split_into_sentences(
        self, text: str, config: ChunkingConfig
    ) -> List[Dict[str, Any]]:
        """
        Split text into sentences with position tracking.

        Args:
            text: Text to split
            config: Chunking configuration

        Returns:
            List of sentence dictionaries with text and position
        """
        sentences = []

        # Try to use NLTK for better sentence splitting
        try:
            import nltk

            try:
                sent_tokenizer = nltk.data.load("tokenizers/punkt/english.pickle")
            except LookupError:
                # Download if not available
                nltk.download("punkt", quiet=True)
                sent_tokenizer = nltk.data.load("tokenizers/punkt/english.pickle")

            sent_spans = list(sent_tokenizer.span_tokenize(text))

            for start, end in sent_spans:
                sentence_text = text[start:end].strip()
                if sentence_text:
                    sentences.append(
                        {
                            "text": sentence_text,
                            "start": start,
                            "end": end,
                        }
                    )

        except ImportError:
            # Fallback to regex-based splitting
            logger.debug("NLTK not available, using regex sentence splitting")
            sentences = self._regex_sentence_split(text)

        return sentences

    def _regex_sentence_split(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into sentences using regex.

        Args:
            text: Text to split

        Returns:
            List of sentence dictionaries
        """
        sentences = []

        # Split by sentence-ending punctuation followed by space and capital
        parts = self.SENTENCE_ENDINGS.split(text)

        current_pos = 0
        for part in parts:
            part = part.strip()
            if part:
                # Find actual position in text
                start = text.find(part, current_pos)
                if start == -1:
                    start = current_pos
                end = start + len(part)

                sentences.append(
                    {
                        "text": part,
                        "start": start,
                        "end": end,
                    }
                )
                current_pos = end

        return sentences

    def _combine_short_sentences(
        self, sentences: List[Dict[str, Any]], config: ChunkingConfig
    ) -> List[Dict[str, Any]]:
        """
        Combine short sentences with adjacent sentences.

        Args:
            sentences: List of sentence dictionaries
            config: Chunking configuration

        Returns:
            List of combined sentence dictionaries
        """
        if not sentences:
            return sentences

        combined = []
        current = None

        for sentence in sentences:
            if current is None:
                current = sentence.copy()
                continue

            # Check if current sentence is short
            if len(current["text"]) < config.sentence_min_length:
                # Combine with next sentence
                current["text"] = current["text"] + " " + sentence["text"]
                current["end"] = sentence["end"]
            else:
                combined.append(current)
                current = sentence.copy()

        # Don't forget the last sentence
        if current:
            combined.append(current)

        return combined

    def _group_sentences_into_chunks(
        self,
        sentences: List[Dict[str, Any]],
        config: ChunkingConfig,
        metadata: Optional[Dict[str, Any]],
        original_text: str,
    ) -> List[Chunk]:
        """
        Group sentences into chunks respecting size limits.

        Args:
            sentences: List of sentence dictionaries
            config: Chunking configuration
            metadata: Base metadata for chunks
            original_text: Original text for position calculation

        Returns:
            List of Chunk objects
        """
        if not sentences:
            return []

        chunks = []
        current_sentences = []
        current_length = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_length = len(sentence["text"])

            # Check if adding this sentence exceeds chunk size
            separator_length = 1 if current_sentences else 0  # Space between sentences
            total_length = current_length + sentence_length + separator_length

            if total_length > config.chunk_size and current_sentences:
                # Create chunk from current sentences
                chunk = self._create_chunk_from_sentences(
                    current_sentences, chunk_index, metadata
                )
                chunks.append(chunk)
                chunk_index += 1

                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_sentences, config
                )
                current_sentences = overlap_sentences + [sentence]
                current_length = sum(len(s["text"]) for s in current_sentences)
                current_length += len(current_sentences) - 1  # Spaces
            else:
                current_sentences.append(sentence)
                current_length = total_length

        # Don't forget the last chunk
        if current_sentences:
            chunk = self._create_chunk_from_sentences(
                current_sentences, chunk_index, metadata
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk_from_sentences(
        self,
        sentences: List[Dict[str, Any]],
        index: int,
        metadata: Optional[Dict[str, Any]],
    ) -> Chunk:
        """
        Create a chunk from a list of sentences.

        Args:
            sentences: List of sentence dictionaries
            index: Chunk index
            metadata: Base metadata

        Returns:
            Chunk object
        """
        content = " ".join(s["text"] for s in sentences)
        start_char = sentences[0]["start"] if sentences else 0
        end_char = sentences[-1]["end"] if sentences else 0

        chunk_metadata = dict(metadata) if metadata else {}
        chunk_metadata["sentence_count"] = len(sentences)

        return self._create_chunk(
            content=content,
            index=index,
            start_char=start_char,
            end_char=end_char,
            base_metadata=chunk_metadata,
        )

    def _get_overlap_sentences(
        self, sentences: List[Dict[str, Any]], config: ChunkingConfig
    ) -> List[Dict[str, Any]]:
        """
        Get sentences for overlap from the end of the current chunk.

        Args:
            sentences: Current chunk's sentences
            config: Chunking configuration

        Returns:
            List of overlap sentences
        """
        if config.chunk_overlap <= 0:
            return []

        overlap_sentences = []
        overlap_length = 0

        # Work backwards from the end
        for sentence in reversed(sentences):
            sentence_length = len(sentence["text"])
            if overlap_length + sentence_length <= config.chunk_overlap:
                overlap_sentences.insert(0, sentence)
                overlap_length += sentence_length + 1  # +1 for space
            else:
                break

        return overlap_sentences
